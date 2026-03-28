from models import ExecutionLog, ArchiveTask
from extensions import db
from sqlalchemy.orm import joinedload


class ExecutionLogService:
    """
    执行日志服务
    """

    @staticmethod
    def get_log_list(page=1, per_page=10, task_id=None, status=None):
        """
        获取执行日志列表
        """
        query = ExecutionLog.query.options(joinedload(ExecutionLog.task))

        if task_id:
            query = query.filter(ExecutionLog.task_id == task_id)

        if status is not None:
            query = query.filter(ExecutionLog.status == status)

        total = query.count()
        logs = query.order_by(ExecutionLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': [log.to_dict() for log in logs.items],
            'total': total,
            'page': page,
            'per_page': per_page
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
