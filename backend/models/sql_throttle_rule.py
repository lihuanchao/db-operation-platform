import json
from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class SqlThrottleRule(db.Model):
    __tablename__ = 'sql_throttle_rule'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    rule_name = db.Column(db.String(100), nullable=False)
    db_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False)
    connection_name = db.Column(db.String(100), nullable=True)
    mysql_version = db.Column(db.String(64), nullable=True)
    enabled = db.Column(db.Integer, nullable=False, default=0)
    slow_sql_seconds = db.Column(db.Integer, nullable=False, default=10)
    fingerprint_concurrency_threshold = db.Column(db.Integer, nullable=False, default=20)
    poll_interval_seconds = db.Column(db.Integer, nullable=False, default=15)
    max_kill_per_round = db.Column(db.Integer, nullable=False, default=10)
    min_rows_examined = db.Column(db.Integer, nullable=True)
    target_db_pattern = db.Column(db.String(255), nullable=True)
    target_user_pattern = db.Column(db.String(255), nullable=True)
    exclude_users = db.Column(db.Text, nullable=True, default='[]')
    exclude_hosts = db.Column(db.Text, nullable=True, default='[]')
    exclude_dbs = db.Column(db.Text, nullable=True, default='[]')
    exclude_fingerprints = db.Column(db.Text, nullable=True, default='[]')
    dry_run = db.Column(db.Integer, nullable=False, default=1)
    kill_command = db.Column(db.String(32), nullable=False, default='KILL QUERY')
    kill_scope = db.Column(db.String(64), nullable=False, default='same_fingerprint_only')
    kill_order = db.Column(db.String(64), nullable=False, default='dup_count_desc_exec_time_desc')
    consecutive_hit_times = db.Column(db.Integer, nullable=False, default=2)
    status = db.Column(db.String(32), nullable=False, default='idle')
    last_run_at = db.Column(db.DateTime, nullable=True)
    last_hit_at = db.Column(db.DateTime, nullable=True)
    last_error_message = db.Column(db.Text, nullable=True)
    creator_user_id = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    db_connection = db.relationship('DbConnection', backref=db.backref('sql_throttle_rules', lazy=True))

    @staticmethod
    def _loads_json_list(raw_value):
        if not raw_value:
            return []
        if isinstance(raw_value, list):
            return raw_value
        try:
            parsed = json.loads(raw_value)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _dumps_json_list(value):
        if value is None:
            return '[]'
        if isinstance(value, str):
            items = [item.strip() for item in value.split(',') if item.strip()]
            return json.dumps(items, ensure_ascii=False)
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return json.dumps(items, ensure_ascii=False)
        return '[]'

    def set_exclude_users(self, value):
        self.exclude_users = self._dumps_json_list(value)

    def set_exclude_hosts(self, value):
        self.exclude_hosts = self._dumps_json_list(value)

    def set_exclude_dbs(self, value):
        self.exclude_dbs = self._dumps_json_list(value)

    def set_exclude_fingerprints(self, value):
        self.exclude_fingerprints = self._dumps_json_list(value)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'db_connection_id': self.db_connection_id,
            'connection_name': self.connection_name,
            'mysql_version': self.mysql_version,
            'enabled': bool(self.enabled),
            'slow_sql_seconds': self.slow_sql_seconds,
            'fingerprint_concurrency_threshold': self.fingerprint_concurrency_threshold,
            'poll_interval_seconds': self.poll_interval_seconds,
            'max_kill_per_round': self.max_kill_per_round,
            'min_rows_examined': self.min_rows_examined,
            'target_db_pattern': self.target_db_pattern,
            'target_user_pattern': self.target_user_pattern,
            'exclude_users': self._loads_json_list(self.exclude_users),
            'exclude_hosts': self._loads_json_list(self.exclude_hosts),
            'exclude_dbs': self._loads_json_list(self.exclude_dbs),
            'exclude_fingerprints': self._loads_json_list(self.exclude_fingerprints),
            'dry_run': bool(self.dry_run),
            'kill_command': self.kill_command,
            'kill_scope': self.kill_scope,
            'kill_order': self.kill_order,
            'consecutive_hit_times': self.consecutive_hit_times,
            'status': self.status,
            'last_run_at': self.last_run_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_run_at else None,
            'last_hit_at': self.last_hit_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_hit_at else None,
            'last_error_message': self.last_error_message,
            'creator_user_id': self.creator_user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
