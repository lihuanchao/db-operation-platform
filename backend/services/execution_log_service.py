from datetime import datetime

from models import ExecutionLog, ArchiveTask
from models.flashback_task import FlashbackTask
from models.sql_throttle_kill_log import SqlThrottleKillLog
from models.sql_throttle_rule import SqlThrottleRule
from models.sql_throttle_run import SqlThrottleRun
from extensions import db
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload


class ExecutionLogService:
    """
    执行日志服务
    """

    @staticmethod
    def normalize_log_type(log_type):
        value = (log_type or '').strip().lower()
        if value in ('flashback', 'archive', 'all', 'merged', 'sql_throttle_run', 'sql_kill'):
            return value
        return 'archive'

    @staticmethod
    def normalize_flashback_status(status):
        """
        将闪回任务状态统一映射为执行日志状态码。
        """
        if status is None:
            return None

        if isinstance(status, int):
            return status if status in (0, 1, 2) else None

        if isinstance(status, str):
            normalized = status.strip().lower()
            if not normalized:
                return None
            if normalized.isdigit():
                value = int(normalized)
                return value if value in (0, 1, 2) else None
            return {
                'completed': 1,
                'queued': 2,
                'running': 2,
                'failed': 0,
            }.get(normalized)

        return None

    @staticmethod
    def _archive_sort_time(log):
        return log.start_time or log.created_at or datetime.min

    @staticmethod
    def _flashback_sort_time(task):
        return task.started_at or task.created_at or datetime.min

    @staticmethod
    def _serialize_archive_log(log):
        item = log.to_dict()
        item.update({
            'log_type': 'archive',
            'detail_path': f'/archive-tasks/{log.task_id}',
        })
        return item

    @classmethod
    def _serialize_flashback_log(cls, task):
        return {
            'id': task.id,
            'task_id': task.id,
            'task_name': f'{task.database_name}.{task.table_name}',
            'cron_job_id': None,
            'start_time': task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else None,
            'end_time': task.finished_at.strftime('%Y-%m-%d %H:%M:%S') if task.finished_at else None,
            'status': cls.normalize_flashback_status(task.status),
            'log_file': None,
            'error_message': task.error_message,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else None,
            'log_type': 'flashback',
            'detail_path': f'/flashback-tasks/{task.id}',
        }

    @staticmethod
    def _status_from_run_status(status):
        normalized = (status or '').strip().lower()
        if normalized == 'completed':
            return 1
        if normalized in ('running', 'queued'):
            return 2
        return 0

    @classmethod
    def _serialize_sql_throttle_run_log(cls, run):
        return {
            'id': run.id,
            'task_id': run.rule_id,
            'task_name': run.rule.rule_name if run.rule else f'规则#{run.rule_id}',
            'cron_job_id': None,
            'start_time': run.sample_started_at.strftime('%Y-%m-%d %H:%M:%S') if run.sample_started_at else None,
            'end_time': run.sample_finished_at.strftime('%Y-%m-%d %H:%M:%S') if run.sample_finished_at else None,
            'status': cls._status_from_run_status(run.status),
            'log_file': None,
            'error_message': run.error_message,
            'created_at': run.created_at.strftime('%Y-%m-%d %H:%M:%S') if run.created_at else None,
            'log_type': 'sql_throttle_run',
            'detail_path': f'/sql-throttle/runs/{run.id}',
            'run_status': run.status,
            'kill_attempt_count': run.kill_attempt_count,
            'kill_success_count': run.kill_success_count,
            'dry_run': bool(run.dry_run),
        }

    @classmethod
    def _serialize_sql_kill_log(cls, kill_log):
        is_success = kill_log.kill_result in ('success', 'dry_run')
        return {
            'id': kill_log.id,
            'task_id': kill_log.rule_id,
            'task_name': kill_log.rule.rule_name if kill_log.rule else f'规则#{kill_log.rule_id}',
            'cron_job_id': None,
            'start_time': kill_log.killed_at.strftime('%Y-%m-%d %H:%M:%S') if kill_log.killed_at else None,
            'end_time': kill_log.killed_at.strftime('%Y-%m-%d %H:%M:%S') if kill_log.killed_at else None,
            'status': 1 if is_success else 0,
            'log_file': None,
            'error_message': kill_log.kill_error_message,
            'created_at': kill_log.created_at.strftime('%Y-%m-%d %H:%M:%S') if kill_log.created_at else None,
            'log_type': 'sql_kill',
            'detail_path': f'/sql-throttle/runs/{kill_log.run_id}',
            'run_id': kill_log.run_id,
            'thread_id': kill_log.thread_id,
            'db_name': kill_log.db_name,
            'fingerprint': kill_log.fingerprint,
            'kill_result': kill_log.kill_result,
        }

    @staticmethod
    def _flashback_task_name_filter(task_name):
        pattern = f'%{task_name}%'
        full_task_name = FlashbackTask.database_name + '.' + FlashbackTask.table_name
        return or_(
            FlashbackTask.database_name.like(pattern),
            FlashbackTask.table_name.like(pattern),
            full_task_name.like(pattern),
        )

    @staticmethod
    def _sql_throttle_rule_name_filter(task_name):
        pattern = f'%{task_name}%'
        return SqlThrottleRule.rule_name.like(pattern)

    @staticmethod
    def _sql_kill_name_filter(task_name):
        pattern = f'%{task_name}%'
        return SqlThrottleRule.rule_name.like(pattern)

    @staticmethod
    def _apply_sort_meta(item, sort_time, sort_id, log_type_rank):
        item['_sort_time'] = sort_time
        item['_sort_id'] = sort_id
        item['_sort_type_rank'] = log_type_rank
        return item

    @classmethod
    def get_log_list(cls, page=1, per_page=10, task_name='', status=None, log_type='', task_id=None):
        """
        获取执行日志列表
        """
        try:
            page = max(int(page), 1)
        except (TypeError, ValueError):
            page = 1

        try:
            per_page = max(int(per_page), 1)
        except (TypeError, ValueError):
            per_page = 10

        status_filter = cls.normalize_flashback_status(status)
        normalized_log_type = cls.normalize_log_type(log_type)
        start = (page - 1) * per_page

        if normalized_log_type == 'archive':
            query = ExecutionLog.query.options(joinedload(ExecutionLog.task)).join(
                ArchiveTask, ArchiveTask.id == ExecutionLog.task_id
            )
            if task_id:
                query = query.filter(ExecutionLog.task_id == task_id)
            if task_name:
                query = query.filter(ArchiveTask.task_name.like(f'%{task_name}%'))
            if status_filter is not None:
                query = query.filter(ExecutionLog.status == status_filter)

            total = query.count()
            logs = query.order_by(
                func.coalesce(ExecutionLog.start_time, ExecutionLog.created_at).desc(),
                ExecutionLog.id.desc(),
            ).paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': [cls._serialize_archive_log(log) for log in logs.items],
                'total': total,
                'page': page,
                'per_page': per_page,
            }

        if normalized_log_type == 'flashback':
            query = FlashbackTask.query
            if task_id:
                query = query.filter(FlashbackTask.id == task_id)
            if task_name:
                query = query.filter(cls._flashback_task_name_filter(task_name))
            if status_filter is not None:
                if status_filter == 1:
                    matched_statuses = ['completed']
                elif status_filter == 2:
                    matched_statuses = ['queued', 'running']
                else:
                    matched_statuses = ['failed']
                query = query.filter(FlashbackTask.status.in_(matched_statuses))

            total = query.count()
            tasks = query.order_by(
                func.coalesce(FlashbackTask.started_at, FlashbackTask.created_at).desc(),
                FlashbackTask.id.desc(),
            ).paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': [cls._serialize_flashback_log(task) for task in tasks.items],
                'total': total,
                'page': page,
                'per_page': per_page,
            }

        if normalized_log_type == 'sql_throttle_run':
            query = SqlThrottleRun.query.options(joinedload(SqlThrottleRun.rule)).join(
                SqlThrottleRule, SqlThrottleRule.id == SqlThrottleRun.rule_id
            )
            if task_id:
                query = query.filter(SqlThrottleRun.rule_id == task_id)
            if task_name:
                query = query.filter(cls._sql_throttle_rule_name_filter(task_name))
            if status_filter is not None:
                if status_filter == 1:
                    query = query.filter(SqlThrottleRun.status == 'completed')
                elif status_filter == 2:
                    query = query.filter(SqlThrottleRun.status.in_(['queued', 'running']))
                else:
                    query = query.filter(SqlThrottleRun.status.in_(['failed', 'skipped']))

            total = query.count()
            rows = query.order_by(
                func.coalesce(SqlThrottleRun.sample_started_at, SqlThrottleRun.created_at).desc(),
                SqlThrottleRun.id.desc(),
            ).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'items': [cls._serialize_sql_throttle_run_log(item) for item in rows.items],
                'total': total,
                'page': page,
                'per_page': per_page,
            }

        if normalized_log_type == 'sql_kill':
            query = SqlThrottleKillLog.query.options(joinedload(SqlThrottleKillLog.rule)).join(
                SqlThrottleRule, SqlThrottleRule.id == SqlThrottleKillLog.rule_id
            )
            if task_id:
                query = query.filter(SqlThrottleKillLog.rule_id == task_id)
            if task_name:
                query = query.filter(cls._sql_kill_name_filter(task_name))
            if status_filter is not None:
                if status_filter == 1:
                    query = query.filter(SqlThrottleKillLog.kill_result.in_(['success', 'dry_run']))
                elif status_filter == 2:
                    query = query.filter(SqlThrottleKillLog.kill_result == 'already_finished')
                else:
                    query = query.filter(SqlThrottleKillLog.kill_result.notin_(['success', 'dry_run']))

            total = query.count()
            rows = query.order_by(
                func.coalesce(SqlThrottleKillLog.killed_at, SqlThrottleKillLog.created_at).desc(),
                SqlThrottleKillLog.id.desc(),
            ).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'items': [cls._serialize_sql_kill_log(item) for item in rows.items],
                'total': total,
                'page': page,
                'per_page': per_page,
            }

        archive_query = ExecutionLog.query.options(joinedload(ExecutionLog.task)).join(
            ArchiveTask, ArchiveTask.id == ExecutionLog.task_id
        )
        if task_id:
            archive_query = archive_query.filter(ExecutionLog.task_id == task_id)
        if task_name:
            archive_query = archive_query.filter(ArchiveTask.task_name.like(f'%{task_name}%'))
        if status_filter is not None:
            archive_query = archive_query.filter(ExecutionLog.status == status_filter)

        flashback_query = FlashbackTask.query
        if task_id:
            flashback_query = flashback_query.filter(FlashbackTask.id == task_id)
        if task_name:
            flashback_query = flashback_query.filter(cls._flashback_task_name_filter(task_name))
        if status_filter is not None:
            if status_filter == 1:
                matched_statuses = ['completed']
            elif status_filter == 2:
                matched_statuses = ['queued', 'running']
            else:
                matched_statuses = ['failed']
            flashback_query = flashback_query.filter(FlashbackTask.status.in_(matched_statuses))

        sql_throttle_run_query = SqlThrottleRun.query.options(joinedload(SqlThrottleRun.rule)).join(
            SqlThrottleRule, SqlThrottleRule.id == SqlThrottleRun.rule_id
        )
        if task_id:
            sql_throttle_run_query = sql_throttle_run_query.filter(SqlThrottleRun.rule_id == task_id)
        if task_name:
            sql_throttle_run_query = sql_throttle_run_query.filter(cls._sql_throttle_rule_name_filter(task_name))
        if status_filter is not None:
            if status_filter == 1:
                sql_throttle_run_query = sql_throttle_run_query.filter(SqlThrottleRun.status == 'completed')
            elif status_filter == 2:
                sql_throttle_run_query = sql_throttle_run_query.filter(SqlThrottleRun.status.in_(['queued', 'running']))
            else:
                sql_throttle_run_query = sql_throttle_run_query.filter(SqlThrottleRun.status.in_(['failed', 'skipped']))

        sql_kill_query = SqlThrottleKillLog.query.options(joinedload(SqlThrottleKillLog.rule)).join(
            SqlThrottleRule, SqlThrottleRule.id == SqlThrottleKillLog.rule_id
        )
        if task_id:
            sql_kill_query = sql_kill_query.filter(SqlThrottleKillLog.rule_id == task_id)
        if task_name:
            sql_kill_query = sql_kill_query.filter(cls._sql_kill_name_filter(task_name))
        if status_filter is not None:
            if status_filter == 1:
                sql_kill_query = sql_kill_query.filter(SqlThrottleKillLog.kill_result.in_(['success', 'dry_run']))
            elif status_filter == 2:
                sql_kill_query = sql_kill_query.filter(SqlThrottleKillLog.kill_result == 'already_finished')
            else:
                sql_kill_query = sql_kill_query.filter(SqlThrottleKillLog.kill_result.notin_(['success', 'dry_run']))

        total = archive_query.count() + flashback_query.count() + sql_throttle_run_query.count() + sql_kill_query.count()
        limit_count = page * per_page
        archive_logs = archive_query.order_by(
            func.coalesce(ExecutionLog.start_time, ExecutionLog.created_at).desc(),
            ExecutionLog.id.desc(),
        ).limit(limit_count).all()
        flashback_tasks = flashback_query.order_by(
            func.coalesce(FlashbackTask.started_at, FlashbackTask.created_at).desc(),
            FlashbackTask.id.desc(),
        ).limit(limit_count).all()
        sql_throttle_runs = sql_throttle_run_query.order_by(
            func.coalesce(SqlThrottleRun.sample_started_at, SqlThrottleRun.created_at).desc(),
            SqlThrottleRun.id.desc(),
        ).limit(limit_count).all()
        sql_kill_logs = sql_kill_query.order_by(
            func.coalesce(SqlThrottleKillLog.killed_at, SqlThrottleKillLog.created_at).desc(),
            SqlThrottleKillLog.id.desc(),
        ).limit(limit_count).all()

        merged_items = []
        for log in archive_logs:
            merged_items.append(cls._apply_sort_meta(
                cls._serialize_archive_log(log),
                cls._archive_sort_time(log),
                log.id or 0,
                0,
            ))
        for task in flashback_tasks:
            merged_items.append(cls._apply_sort_meta(
                cls._serialize_flashback_log(task),
                cls._flashback_sort_time(task),
                task.id or 0,
                1,
            ))
        for run in sql_throttle_runs:
            merged_items.append(cls._apply_sort_meta(
                cls._serialize_sql_throttle_run_log(run),
                run.sample_started_at or run.created_at or datetime.min,
                run.id or 0,
                2,
            ))
        for kill_log in sql_kill_logs:
            merged_items.append(cls._apply_sort_meta(
                cls._serialize_sql_kill_log(kill_log),
                kill_log.killed_at or kill_log.created_at or datetime.min,
                kill_log.id or 0,
                3,
            ))

        merged_items.sort(
            key=lambda item: (item['_sort_time'], item['_sort_id'], item['_sort_type_rank']),
            reverse=True,
        )

        items = []
        for item in merged_items[start:start + per_page]:
            cleaned = dict(item)
            cleaned.pop('_sort_time', None)
            cleaned.pop('_sort_id', None)
            cleaned.pop('_sort_type_rank', None)
            items.append(cleaned)

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
        }

    @staticmethod
    def get_log_detail(log_id):
        """
        获取执行日志详情
        """
        log = ExecutionLog.query.options(joinedload(ExecutionLog.task)).get(log_id)
        if not log:
            return None
        return log.to_dict()

    @staticmethod
    def get_sql_throttle_run_log_content(log_id):
        run = db.session.get(SqlThrottleRun, log_id)
        if not run:
            return None
        lines = [
            f'run_id: {run.id}',
            f'rule_id: {run.rule_id}',
            f'rule_name: {run.rule.rule_name if run.rule else ""}',
            f'status: {run.status}',
            f'dry_run: {bool(run.dry_run)}',
            f'total_session_count: {run.total_session_count}',
            f'candidate_fingerprint_count: {run.candidate_fingerprint_count}',
            f'hit_fingerprint_count: {run.hit_fingerprint_count}',
            f'kill_attempt_count: {run.kill_attempt_count}',
            f'kill_success_count: {run.kill_success_count}',
            f'error_message: {run.error_message or ""}',
        ]
        return '\n'.join(lines)

    @staticmethod
    def get_sql_kill_log_content(log_id):
        kill_log = db.session.get(SqlThrottleKillLog, log_id)
        if not kill_log:
            return None
        lines = [
            f'kill_log_id: {kill_log.id}',
            f'run_id: {kill_log.run_id}',
            f'rule_id: {kill_log.rule_id}',
            f'rule_name: {kill_log.rule.rule_name if kill_log.rule else ""}',
            f'thread_id: {kill_log.thread_id}',
            f'db_user: {kill_log.db_user or ""}',
            f'db_host: {kill_log.db_host or ""}',
            f'db_name: {kill_log.db_name or ""}',
            f'kill_command: {kill_log.kill_command}',
            f'kill_result: {kill_log.kill_result}',
            f'kill_error_message: {kill_log.kill_error_message or ""}',
        ]
        return '\n'.join(lines)

    @staticmethod
    def create_log(data):
        """
        创建执行日志
        """
        try:
            log = ExecutionLog(
                task_id=data['task_id'],
                cron_job_id=data.get('cron_job_id'),
                start_time=data['start_time'],
                end_time=data.get('end_time'),
                status=data.get('status', 0),
                log_file=data.get('log_file'),
                error_message=data.get('error_message')
            )

            db.session.add(log)
            db.session.commit()

            return log.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_log(log_id, data):
        """
        更新执行日志
        """
        try:
            log = ExecutionLog.query.get(log_id)
            if not log:
                return None, '日志不存在'

            if 'end_time' in data:
                log.end_time = data['end_time']

            if 'status' in data:
                log.status = data['status']

            if 'log_file' in data:
                log.log_file = data['log_file']

            if 'error_message' in data:
                log.error_message = data['error_message']

            db.session.commit()

            return log.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
