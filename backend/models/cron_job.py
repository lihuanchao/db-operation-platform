from datetime import datetime
from extensions import db


class CronJob(db.Model):
    __tablename__ = 'cron_job'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='定时任务ID')
    task_id = db.Column(db.BigInteger, db.ForeignKey('archive_task.id'), nullable=False, comment='归档任务ID')
    cron_expression = db.Column(db.String(50), nullable=False, comment='Cron表达式')
    next_run_time = db.Column(db.DateTime, nullable=True, comment='下次运行时间')
    last_run_time = db.Column(db.DateTime, nullable=True, comment='上次运行时间')
    is_active = db.Column(db.Integer, nullable=False, default=1, comment='是否激活')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    task = db.relationship('ArchiveTask', backref=db.backref('cron_jobs', lazy=True))

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'cron_expression': self.cron_expression,
            'next_run_time': self.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if self.next_run_time else None,
            'last_run_time': self.last_run_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_run_time else None,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def __repr__(self):
        return f'<CronJob {self.cron_expression}>'
