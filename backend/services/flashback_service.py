import subprocess
import threading
from datetime import datetime
import glob
import os

from extensions import db
from models.db_connection import DbConnection
from models.flashback_task import FlashbackTask


class FlashbackService:
    TOOL_PATH = '/my2sql'
    OUTPUT_ROOT = '/app/flashback/tasks'

    @classmethod
    def _task_root(cls, task_id):
        return os.path.realpath(os.path.join(cls.OUTPUT_ROOT, str(task_id)))

    @classmethod
    def _resolve_task_path(cls, task_id, path):
        if not path or not isinstance(path, str):
            return None

        task_root = cls._task_root(task_id)
        candidate = path if os.path.isabs(path) else os.path.join(task_root, path)
        candidate = os.path.realpath(candidate)

        try:
            if os.path.commonpath([task_root, candidate]) != task_root:
                return None
        except ValueError:
            return None

        return candidate

    @classmethod
    def build_command(cls, task, connection, output_dir):
        command = [
            cls.TOOL_PATH,
            '-databases', task.database_name,
            '-tables', task.table_name,
            '-mode', task.mode or 'repl',
            '-host', connection.host,
            '-port', str(connection.port),
            '-user', connection.username,
            '-password', connection.password,
            '-sql', task.sql_type,
        ]

        optional_pairs = [
            ('-start-datetime', task.start_datetime),
            ('-stop-datetime', task.stop_datetime),
            ('-start-file', task.start_file),
            ('-stop-file', task.stop_file),
        ]
        for flag, value in optional_pairs:
            if value:
                command.extend([flag, value])

        command.extend([
            '-work-type', task.work_type,
            '-output-dir', output_dir,
        ])
        return command, cls.mask_command(command)

    @classmethod
    def get_task_list(cls, page=1, per_page=10, database_name='', table_name='', status='', sql_type='', work_type=''):
        page, per_page = cls._normalize_pagination(page, per_page)
        query = FlashbackTask.query

        if database_name:
            query = query.filter(FlashbackTask.database_name.like(f'%{database_name}%'))
        if table_name:
            query = query.filter(FlashbackTask.table_name.like(f'%{table_name}%'))
        if status:
            query = query.filter(FlashbackTask.status == status)
        if sql_type:
            query = query.filter(FlashbackTask.sql_type == sql_type)
        if work_type:
            query = query.filter(FlashbackTask.work_type == work_type)

        total = query.count()
        tasks = query.order_by(FlashbackTask.created_at.desc(), FlashbackTask.id.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        total_pages = (total + per_page - 1) // per_page if total else 1
        return {
            'items': [task.to_dict() for task in tasks.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < total_pages else None,
            },
        }

    @staticmethod
    def get_task_detail(task_id):
        task = db.session.get(FlashbackTask, task_id)
        if not task:
            return None
        return task.to_dict()

    @classmethod
    def get_log_content(cls, task_id):
        task = db.session.get(FlashbackTask, task_id)
        if not task:
            return None, '闪回任务不存在'

        if not task.log_file:
            return {'content': '', 'has_file': False}, None

        log_file = cls._resolve_task_path(task_id, task.log_file)
        if not log_file:
            return None, '日志文件路径越界'

        if not os.path.exists(log_file):
            return {'content': '', 'has_file': False}, None

        try:
            with open(log_file, 'r', encoding='utf-8') as file_obj:
                return {'content': file_obj.read(), 'has_file': True}, None
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def resolve_download_file(cls, task_id, artifact_id=None):
        task = db.session.get(FlashbackTask, task_id)
        if not task:
            return None, '闪回任务不存在'

        if not artifact_id:
            if not task.log_file:
                return None, '日志文件不存在'
            log_file = cls._resolve_task_path(task_id, task.log_file)
            if not log_file:
                return None, '日志文件路径越界'
            if not os.path.exists(log_file):
                return None, '日志文件不存在'
            return log_file, None

        for item in task.get_artifacts():
            if item.get('id') == artifact_id:
                artifact_path = item.get('path')
                if not artifact_path:
                    return None, '产物文件不存在'
                resolved_path = cls._resolve_task_path(task_id, artifact_path)
                if not resolved_path:
                    return None, '产物文件路径越界'
                if not os.path.exists(resolved_path):
                    return None, '产物文件不存在'
                return resolved_path, None

        return None, '产物文件不存在'

    @classmethod
    def create_task(cls, data, current_user=None):
        try:
            required_fields = ['db_connection_id', 'database_name', 'table_name', 'sql_type', 'work_type']
            for field in required_fields:
                if field not in data or data[field] in (None, ''):
                    return None, f'{field} 是必填字段'

            try:
                db_connection_id = int(data['db_connection_id'])
            except (TypeError, ValueError):
                return None, 'db_connection_id 必须为整数'

            db_connection = db.session.get(DbConnection, db_connection_id)
            if not db_connection or db_connection.is_enabled == 0:
                return None, '数据库连接不存在或已禁用'

            task = FlashbackTask(
                db_connection_id=db_connection.id,
                connection_id=db_connection.id,
                connection_name=db_connection.connection_name,
                database_name=data['database_name'],
                table_name=data['table_name'],
                mode='repl',
                sql_type=data['sql_type'],
                work_type=data['work_type'],
                start_datetime=data.get('start_datetime'),
                stop_datetime=data.get('stop_datetime'),
                start_file=data.get('start_file'),
                stop_file=data.get('stop_file'),
                status='queued',
                progress=0,
                creator_user_id=current_user.id if current_user else None,
                creator_employee_no=current_user.employee_no if current_user else None,
            )

            db.session.add(task)
            db.session.commit()

            started, start_error = cls._run_task_async(task.id)
            if not started:
                return None, start_error or '异步任务启动失败'
            return task.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            return None, str(exc)

    @classmethod
    def _run_task_async(cls, task_id):
        from app import app

        task = db.session.get(FlashbackTask, task_id)
        if not task:
            return False, '任务不存在'

        def _worker():
            with app.app_context():
                cls._execute_task(task_id)

        try:
            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()
            return True, None
        except Exception as exc:
            error_message = f'异步任务启动失败: {exc}'
            task = db.session.get(FlashbackTask, task_id)
            if task:
                cls._mark_failed(task, error_message)
            return False, error_message

    @classmethod
    def _execute_task(cls, task_id):
        task = db.session.get(FlashbackTask, task_id)
        if not task:
            return

        connection = db.session.get(DbConnection, task.db_connection_id)
        if not connection or connection.is_enabled == 0:
            cls._mark_failed(task, '数据库连接不存在或已禁用')
            return

        try:
            task_dir = os.path.join(cls.OUTPUT_ROOT, str(task.id))
            output_dir = os.path.join(task_dir, 'output')
            log_file = os.path.join(task_dir, 'run.log')
            os.makedirs(output_dir, exist_ok=True)

            command, masked_command = cls.build_command(task, connection, output_dir)
            task.output_dir = output_dir
            task.log_file = log_file
            task.status = 'running'
            task.progress = 30
            task.started_at = datetime.now()
            task.masked_command = masked_command
            task.error_message = None
            db.session.commit()

            with open(log_file, 'a', encoding='utf-8') as log_fp:
                process = subprocess.Popen(command, stdout=log_fp, stderr=log_fp, text=True)
                return_code = process.wait()

            if return_code != 0:
                task.status = 'failed'
                task.progress = 100
                task.finished_at = datetime.now()
                task.error_message = f'命令执行失败，退出码: {return_code}'
                db.session.commit()
                return

            artifacts = cls.collect_artifacts(output_dir)
            task.set_artifacts(artifacts)
            task.status = 'completed'
            task.progress = 100
            task.finished_at = datetime.now()
            task.error_message = None
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            task = db.session.get(FlashbackTask, task_id)
            if task:
                cls._mark_failed(task, str(exc))

    @staticmethod
    def _mark_failed(task, error_message):
        task.status = 'failed'
        task.progress = 100
        task.error_message = error_message
        task.finished_at = datetime.now()
        db.session.commit()

    @staticmethod
    def mask_command(command):
        masked = list(command)
        for index, part in enumerate(masked):
            if part == '-password' and index + 1 < len(masked):
                masked[index + 1] = '******'
        return ' '.join(masked)

    @staticmethod
    def collect_artifacts(output_dir):
        items = []
        for artifact_id, name in (
            ('binlog-status', 'binlog_status.txt'),
            ('biglong-trx', 'biglong_trx.txt'),
        ):
            path = os.path.join(output_dir, name)
            if not os.path.exists(path):
                raise FileNotFoundError(name)
            items.append({
                'id': artifact_id,
                'name': name,
                'path': path,
                'size': os.path.getsize(path),
            })

        sql_files = sorted(glob.glob(os.path.join(output_dir, '*.sql')), key=os.path.basename)
        if not sql_files:
            raise FileNotFoundError('*.sql')
        sql_path = sql_files[0]
        items.append({
            'id': 'result-sql',
            'name': os.path.basename(sql_path),
            'path': sql_path,
            'size': os.path.getsize(sql_path),
        })
        return items

    @staticmethod
    def _normalize_pagination(page, per_page):
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1

        try:
            per_page = int(per_page)
        except (TypeError, ValueError):
            per_page = 10

        return max(page, 1), max(per_page, 1)
