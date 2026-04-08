from datetime import datetime

from models import ExecutionLog, ArchiveTask
from models.flashback_task import FlashbackTask
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
        if value in ('flashback', 'archive', 'all', 'merged'):
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
                query = query.filter(
                    or_(
                        FlashbackTask.database_name.like(f'%{task_name}%'),
                        FlashbackTask.table_name.like(f'%{task_name}%'),
                    )
                )
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
            flashback_query = flashback_query.filter(
                or_(
                    FlashbackTask.database_name.like(f'%{task_name}%'),
                    FlashbackTask.table_name.like(f'%{task_name}%'),
                )
            )
        if status_filter is not None:
            if status_filter == 1:
                matched_statuses = ['completed']
            elif status_filter == 2:
                matched_statuses = ['queued', 'running']
            else:
                matched_statuses = ['failed']
            flashback_query = flashback_query.filter(FlashbackTask.status.in_(matched_statuses))

        total = archive_query.count() + flashback_query.count()
        limit_count = page * per_page
        archive_logs = archive_query.order_by(
            func.coalesce(ExecutionLog.start_time, ExecutionLog.created_at).desc(),
            ExecutionLog.id.desc(),
        ).limit(limit_count).all()
        flashback_tasks = flashback_query.order_by(
            func.coalesce(FlashbackTask.started_at, FlashbackTask.created_at).desc(),
            FlashbackTask.id.desc(),
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
