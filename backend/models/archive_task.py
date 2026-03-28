from datetime import datetime
from extensions import db


class ArchiveTask(db.Model):
    __tablename__ = 'archive_task'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='任务ID')
    task_name = db.Column(db.String(100), nullable=False, comment='任务名称')
    source_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False, comment='源库连接ID')
    source_database = db.Column(db.String(100), nullable=False, comment='源库名称')
    source_table = db.Column(db.String(100), nullable=False, comment='源表名称')
    dest_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=True, comment='目标库连接ID（可选）')
    dest_database = db.Column(db.String(100), nullable=True, comment='目标库名称（可选）')
    dest_table = db.Column(db.String(100), nullable=True, comment='目标表名称（可选）')
    where_condition = db.Column(db.Text, nullable=True, comment='归档条件（WHERE子句）')
    is_enabled = db.Column(db.Integer, nullable=False, default=1, comment='是否启用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    source_connection = db.relationship('DbConnection', foreign_keys=[source_connection_id], backref=db.backref('source_tasks', lazy=True))
    dest_connection = db.relationship('DbConnection', foreign_keys=[dest_connection_id], backref=db.backref('dest_tasks', lazy=True))

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'task_name': self.task_name,
            'source_connection_id': self.source_connection_id,
            'source_database': self.source_database,
            'source_table': self.source_table,
            'dest_connection_id': self.dest_connection_id,
            'dest_database': self.dest_database,
            'dest_table': self.dest_table,
            'where_condition': self.where_condition,
            'is_enabled': bool(self.is_enabled),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'source_connection': self.source_connection.to_dict() if self.source_connection else None,
            'dest_connection': self.dest_connection.to_dict() if self.dest_connection else None
        }

    def __repr__(self):
        return f'<ArchiveTask {self.task_name}>'
