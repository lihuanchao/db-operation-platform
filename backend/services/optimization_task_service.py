import re
import threading
from datetime import datetime
from typing import Optional, Tuple

from extensions import db
from models import DbConnection, OptimizationTask
from services.access_control_service import AccessControlService
from services.llm_service import LLMService


class OptimizationTaskService:
    ALLOWED_TYPES = {'sql', 'mybatis'}

    @classmethod
    def get_task_list(cls, page=1, per_page=10, task_type='', current_user=None):
        query = cls._build_scoped_query(task_type=task_type, current_user=current_user)

        total = query.count()
        tasks = query.order_by(OptimizationTask.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return {
            'items': [task.to_dict() for task in tasks.items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @classmethod
    def get_task_detail(cls, task_id, current_user=None):
        query = cls._build_scoped_query(current_user=current_user)
        task = query.filter(OptimizationTask.id == task_id).first()
        if not task:
            return None
        data = task.to_dict(include_content=True)
        if task.full_suggestion:
            writing_optimization, index_recommendation, optimized_content, matched_rules = cls.extract_sections(task.full_suggestion)
            data['writing_optimization'] = writing_optimization
            data['index_recommendation'] = index_recommendation
            data['optimized_content'] = optimized_content or data.get('optimized_content') or task.object_content
            data['matched_rules'] = matched_rules
        else:
            data['matched_rules'] = ''
            data['index_recommendation'] = cls._normalize_index_recommendation(data.get('index_recommendation', ''))
        return data

    @classmethod
    def create_task(cls, task_type: str, db_connection_id: int, database_name: str, object_content: str, current_user=None):
        task_type = (task_type or '').strip().lower()
        if task_type not in cls.ALLOWED_TYPES:
            return None, '无效的任务类型'

        object_content = (object_content or '').strip()
        if not object_content:
            return None, '优化内容不能为空'

        database_name = (database_name or '').strip()
        if not database_name:
            return None, '数据库名称不能为空'

        db_connection = DbConnection.query.get(db_connection_id)
        if not db_connection or db_connection.is_enabled == 0:
            return None, '数据库连接不存在或已禁用'
        if current_user is not None:
            AccessControlService.ensure_connection_access(current_user, db_connection.id)

        preview = cls._build_preview(object_content)
        task = OptimizationTask(
            task_type=task_type,
            object_content=object_content,
            object_preview=preview,
            db_connection_id=db_connection.id,
            connection_id=db_connection.id,
            database_name=database_name,
            database_host=db_connection.host,
            creator_user_id=current_user.id if current_user else None,
            creator_employee_no=current_user.employee_no if current_user else None,
            status='queued',
            progress=0
        )

        db.session.add(task)
        db.session.commit()

        cls._run_task_async(task.id)
        return task.to_dict(), None

    @classmethod
    def _build_scoped_query(cls, task_type='', current_user=None):
        query = OptimizationTask.query
        if task_type:
            query = query.filter(OptimizationTask.task_type == task_type)

        if current_user and current_user.role_code != 'admin':
            authorized_ids = AccessControlService.authorized_connection_ids(current_user) or [-1]
            query = query.filter(
                OptimizationTask.creator_user_id == current_user.id,
                OptimizationTask.connection_id.in_(authorized_ids)
            )
        return query

    @classmethod
    def _run_task_async(cls, task_id: int):
        from app import app  # 延迟导入，避免循环引用

        def _worker():
            with app.app_context():
                cls._execute_task(task_id)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    @classmethod
    def _execute_task(cls, task_id: int):
        task = OptimizationTask.query.get(task_id)
        if not task:
            return

        db_connection = DbConnection.query.get(task.db_connection_id)
        if not db_connection or db_connection.is_enabled == 0:
            cls._mark_failed(task, '数据库连接不存在或已禁用')
            return

        try:
            task.status = 'running'
            task.progress = 25
            task.started_at = datetime.now()
            task.error_message = None
            db.session.commit()

            llm_service = LLMService()
            host = db_connection.manage_host or db_connection.host
            suggestion = llm_service.get_optimization_suggestion(
                task.object_content,
                db_connection=db_connection,
                host=host,
                database_name=task.database_name
            )

            if not suggestion:
                raise ValueError('未获取到优化建议结果')
            if suggestion.startswith('❌') or suggestion.startswith('⚠️'):
                raise ValueError(suggestion)

            writing_optimization, index_recommendation, optimized_content, _ = cls.extract_sections(suggestion)

            task.status = 'completed'
            task.progress = 100
            task.writing_optimization = writing_optimization
            task.index_recommendation = index_recommendation
            task.optimized_content = optimized_content
            task.full_suggestion = suggestion
            task.finished_at = datetime.now()
            task.error_message = None
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            task = OptimizationTask.query.get(task_id)
            if task:
                cls._mark_failed(task, str(exc))

    @classmethod
    def _mark_failed(cls, task: OptimizationTask, error_message: str):
        task.status = 'failed'
        task.progress = 100
        task.error_message = error_message
        task.finished_at = datetime.now()
        db.session.commit()

    @staticmethod
    def _build_preview(content: str) -> str:
        cleaned = ' '.join(content.replace('\r', '\n').split())
        if len(cleaned) <= 80:
            return cleaned
        return f'{cleaned[:80]}...'

    @classmethod
    def extract_sections(cls, suggestion: str) -> Tuple[str, str, Optional[str], str]:
        writing = cls._extract_by_titles(
            suggestion,
            titles=['SQL重写', '写法优化', '优化后SQL', '最终优化后', '优化方案']
        )
        index = cls._extract_by_titles(
            suggestion,
            titles=['索引推荐', '索引策略', '表结构改造', 'ALTER TABLE', 'CREATE INDEX']
        )

        if not writing:
            writing = suggestion.strip()
        if not index:
            index = cls._extract_index_fallback(suggestion)

        index = cls._normalize_index_recommendation(index)
        optimized_content = cls._extract_optimized_content(writing, suggestion)
        matched_rules = cls._extract_hit_rules(suggestion)
        return writing, index, optimized_content, matched_rules

    @staticmethod
    def _extract_by_titles(content: str, titles) -> str:
        lines = content.splitlines()
        start_idx = None
        end_idx = None

        for idx, line in enumerate(lines):
            normalized = line.strip().lower()
            if not normalized:
                continue
            if any(title.lower() in normalized for title in titles):
                start_idx = idx + 1
                break

        if start_idx is None:
            return ''

        for idx in range(start_idx, len(lines)):
            line = lines[idx].strip()
            if line.startswith('#') and idx > start_idx:
                end_idx = idx
                break

        selected = lines[start_idx:end_idx] if end_idx is not None else lines[start_idx:]
        return '\n'.join(selected).strip()

    @staticmethod
    def _extract_index_fallback(content: str) -> str:
        sql_statements = []
        for line in content.splitlines():
            stripped = line.strip()
            upper = stripped.upper()
            if upper.startswith('CREATE INDEX') or upper.startswith('ALTER TABLE') or 'ADD INDEX' in upper:
                sql_statements.append(stripped)
        return '\n'.join(sql_statements).strip()

    @staticmethod
    def _extract_last_code_block(content: str) -> Optional[str]:
        matches = re.findall(r'```(?:sql|xml)?\s*(.*?)```', content, flags=re.IGNORECASE | re.DOTALL)
        if not matches:
            return None
        return matches[-1].strip() or None

    @classmethod
    def _extract_optimized_content(cls, writing_section: str, full_content: str) -> Optional[str]:
        for source in [writing_section, full_content]:
            blocks = re.findall(r'```(?:sql|xml)?\s*(.*?)```', source, flags=re.IGNORECASE | re.DOTALL)
            candidate = cls._pick_query_like_block(blocks)
            if candidate:
                return candidate
        return None

    @staticmethod
    def _strip_sql_comments(sql_text: str) -> str:
        text = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('--') or stripped.startswith('#'):
                continue
            lines.append(line)
        return '\n'.join(lines).strip()

    @classmethod
    def _pick_query_like_block(cls, blocks) -> Optional[str]:
        if not blocks:
            return None

        ddl_prefixes = (
            'create ', 'alter ', 'drop ', 'truncate ', 'rename ', 'grant ',
            'revoke ', 'use ', 'set ', 'show ', 'desc '
        )

        cleaned_blocks = []
        for block in blocks:
            cleaned = cls._strip_sql_comments(block)
            if not cleaned:
                continue
            normalized = cleaned.lstrip().lower()
            cleaned_blocks.append((cleaned, normalized))

        for cleaned, normalized in cleaned_blocks:
            if normalized.startswith('<') or '<select' in normalized or '<mapper' in normalized:
                return cleaned
            if normalized.startswith('with ') or normalized.startswith('select '):
                return cleaned

        for cleaned, normalized in cleaned_blocks:
            if normalized.startswith(ddl_prefixes):
                continue
            return cleaned

        return None

    @staticmethod
    def _extract_hit_rules(content: str) -> str:
        rules = re.findall(r'\b(rule\d{1,2})\b', content, flags=re.IGNORECASE)
        unique_rules = []
        for rule in rules:
            normalized = rule.lower()
            if normalized not in unique_rules:
                unique_rules.append(normalized)
        return ', '.join(unique_rules)

    @staticmethod
    def _normalize_index_recommendation(content: str) -> str:
        if not content:
            return '暂无索引推荐'

        text = re.sub(r'(?is)\*\*预期收益\*\*.*$', '', content).strip()
        text = re.sub(r'(?is)预期收益[:：].*$', '', text).strip()

        lines = text.splitlines()
        statements = []
        buffer = []

        def _flush():
            nonlocal buffer
            if not buffer:
                return
            candidate = '\n'.join(buffer).strip()
            if candidate:
                statements.append(candidate)
            buffer = []

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            upper = stripped.upper()

            starts_stmt = (
                upper.startswith('CREATE INDEX')
                or upper.startswith('CREATE UNIQUE INDEX')
                or upper.startswith('ALTER TABLE')
            )

            if starts_stmt and not buffer:
                buffer.append(line)
                if ';' in stripped:
                    _flush()
                continue

            if buffer:
                buffer.append(line)
                if ';' in stripped:
                    _flush()
                continue

        _flush()

        if not statements:
            return '无需新增索引'

        normalized_statements = []
        for statement in statements:
            cleaned = '\n'.join(line.rstrip() for line in statement.strip().splitlines())
            if cleaned:
                normalized_statements.append(cleaned)

        if not normalized_statements:
            return '无需新增索引'

        return '\n\n'.join(normalized_statements)
