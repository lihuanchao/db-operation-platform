from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class SqlThrottleKillLog(db.Model):
    __tablename__ = 'sql_throttle_kill_log'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    run_id = db.Column(db.BigInteger, db.ForeignKey('sql_throttle_run.id'), nullable=False)
    rule_id = db.Column(db.BigInteger, db.ForeignKey('sql_throttle_rule.id'), nullable=False)
    thread_id = db.Column(db.BigInteger, nullable=False)
    db_user = db.Column(db.String(128), nullable=True)
    db_host = db.Column(db.String(255), nullable=True)
    db_name = db.Column(db.String(255), nullable=True)
    fingerprint = db.Column(db.Text, nullable=True)
    sample_sql_text = db.Column(db.Text, nullable=True)
    exec_time_seconds = db.Column(db.Integer, nullable=False, default=0)
    kill_command = db.Column(db.String(32), nullable=False, default='KILL QUERY')
    kill_result = db.Column(db.String(32), nullable=False, default='failed')
    kill_error_message = db.Column(db.Text, nullable=True)
    killed_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    run = db.relationship('SqlThrottleRun', backref=db.backref('kill_logs', lazy=True))
    rule = db.relationship('SqlThrottleRule', backref=db.backref('kill_logs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule.rule_name if self.rule else None,
            'thread_id': self.thread_id,
            'db_user': self.db_user,
            'db_host': self.db_host,
            'db_name': self.db_name,
            'fingerprint': self.fingerprint,
            'sample_sql_text': self.sample_sql_text,
            'exec_time_seconds': self.exec_time_seconds,
            'kill_command': self.kill_command,
            'kill_result': self.kill_result,
            'kill_error_message': self.kill_error_message,
            'killed_at': self.killed_at.strftime('%Y-%m-%d %H:%M:%S') if self.killed_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
