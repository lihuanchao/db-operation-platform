from datetime import datetime

from extensions import db


class OptimizationTask(db.Model):
    __tablename__ = 'optimization_task'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='优化任务ID')
    task_type = db.Column(db.String(20), nullable=False, comment='任务类型：sql/mybatis')
    object_content = db.Column(db.Text, nullable=False, comment='待优化对象内容(SQL/XML)')
    object_preview = db.Column(db.String(255), nullable=False, comment='对象预览')
    db_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False, comment='数据库连接ID')
    database_name = db.Column(db.String(100), nullable=False, comment='数据库名称')
    database_host = db.Column(db.String(100), nullable=False, comment='数据库IP')
    status = db.Column(db.String(20), nullable=False, default='queued', comment='状态：queued/running/completed/failed')
    progress = db.Column(db.Integer, nullable=False, default=0, comment='优化进度百分比')
    writing_optimization = db.Column(db.Text, nullable=True, comment='写法优化建议')
    index_recommendation = db.Column(db.Text, nullable=True, comment='索引推荐')
    optimized_content = db.Column(db.Text, nullable=True, comment='最终优化后的SQL/XML')
    full_suggestion = db.Column(db.Text, nullable=True, comment='完整优化建议')
    error_message = db.Column(db.Text, nullable=True, comment='错误信息')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    started_at = db.Column(db.DateTime, nullable=True, comment='开始时间')
    finished_at = db.Column(db.DateTime, nullable=True, comment='完成时间')

    db_connection = db.relationship('DbConnection', backref=db.backref('optimization_tasks', lazy=True))

    def to_dict(self, include_content=False):
        data = {
            'id': self.id,
            'task_type': self.task_type,
            'object_preview': self.object_preview,
            'db_connection_id': self.db_connection_id,
            'database_name': self.database_name,
            'database_host': self.database_host,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            'finished_at': self.finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.finished_at else None
        }
        if include_content:
            data.update({
                'object_content': self.object_content,
                'writing_optimization': self.writing_optimization,
                'index_recommendation': self.index_recommendation,
                'optimized_content': self.optimized_content,
                'full_suggestion': self.full_suggestion
            })
        return data

    def __repr__(self):
        return f'<OptimizationTask {self.id}:{self.task_type}>'
