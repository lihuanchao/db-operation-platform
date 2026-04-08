import json
from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FlashbackTask(db.Model):
    __tablename__ = 'flashback_task'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    db_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False)
    connection_id = db.Column(db.BigInteger, nullable=True)
    connection_name = db.Column(db.String(100), nullable=False)
    database_name = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default='repl')
    sql_type = db.Column(db.String(20), nullable=False)
    work_type = db.Column(db.String(20), nullable=False)
    start_datetime = db.Column(db.String(32), nullable=True)
    stop_datetime = db.Column(db.String(32), nullable=True)
    start_file = db.Column(db.String(128), nullable=True)
    stop_file = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='queued')
    progress = db.Column(db.Integer, nullable=False, default=0)
    output_dir = db.Column(db.String(500), nullable=True)
    log_file = db.Column(db.String(500), nullable=True)
    masked_command = db.Column(db.Text, nullable=True)
    artifact_manifest = db.Column(db.Text, nullable=True, default='[]')
    error_message = db.Column(db.Text, nullable=True)
    creator_user_id = db.Column(db.BigInteger, nullable=True)
    creator_employee_no = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    db_connection = db.relationship('DbConnection', backref=db.backref('flashback_tasks', lazy=True))

    def set_artifacts(self, artifacts):
        self.artifact_manifest = json.dumps(artifacts or [], ensure_ascii=False)

    def get_artifacts(self):
        if not self.artifact_manifest:
            return []
        try:
            return json.loads(self.artifact_manifest)
        except (TypeError, ValueError):
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'db_connection_id': self.db_connection_id,
            'connection_id': self.connection_id,
            'connection_name': self.connection_name,
            'database_name': self.database_name,
            'table_name': self.table_name,
            'mode': self.mode,
            'sql_type': self.sql_type,
            'work_type': self.work_type,
            'start_datetime': self.start_datetime,
            'stop_datetime': self.stop_datetime,
            'start_file': self.start_file,
            'stop_file': self.stop_file,
            'status': self.status,
            'progress': self.progress,
            'output_dir': self.output_dir,
            'log_file': self.log_file,
            'masked_command': self.masked_command,
            'artifacts': self.get_artifacts(),
            'error_message': self.error_message,
            'creator_user_id': self.creator_user_id,
            'creator_employee_no': self.creator_employee_no,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            'finished_at': self.finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.finished_at else None,
        }

