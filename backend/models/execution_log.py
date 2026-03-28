from datetime import datetime
from extensions import db


class ExecutionLog(db.Model):
    __tablename__ = 'execution_log'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='执行日志ID')
    task_id = db.Column(db.BigInteger, db.ForeignKey('archive_task.id'), nullable=False, comment='归档任务ID')
    cron_job_id = db.Column(db.BigInteger, db.ForeignKey('cron_job.id'), nullable=True, comment='定时任务ID')
    start_time = db.Column(db.DateTime, nullable=False, comment='开始时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='结束时间')
    status = db.Column(db.Integer, nullable=False, default=0, comment='执行状态：0-失败，1-成功，2-执行中')
    log_file = db.Column(db.String(500), nullable=True, comment='日志文件路径')
    error_message = db.Column(db.Text, nullable=True, comment='错误信息')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')

    # 关系
    task = db.relationship('ArchiveTask', backref=db.backref('execution_logs', lazy=True))
    cron_job = db.relationship('CronJob', backref=db.backref('execution_logs', lazy=True))

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'cron_job_id': self.cron_job_id,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'status': self.status,
            'log_file': self.log_file,
            'error_message': self.error_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<ExecutionLog {self.id}>'
