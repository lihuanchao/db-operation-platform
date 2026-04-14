import json
from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class SqlThrottleRun(db.Model):
    __tablename__ = 'sql_throttle_run'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    rule_id = db.Column(db.BigInteger, db.ForeignKey('sql_throttle_rule.id'), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='queued')
    sample_started_at = db.Column(db.DateTime, nullable=True)
    sample_finished_at = db.Column(db.DateTime, nullable=True)
    total_session_count = db.Column(db.Integer, nullable=False, default=0)
    candidate_fingerprint_count = db.Column(db.Integer, nullable=False, default=0)
    hit_fingerprint_count = db.Column(db.Integer, nullable=False, default=0)
    kill_attempt_count = db.Column(db.Integer, nullable=False, default=0)
    kill_success_count = db.Column(db.Integer, nullable=False, default=0)
    dry_run = db.Column(db.Integer, nullable=False, default=1)
    error_message = db.Column(db.Text, nullable=True)
    snapshot_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    rule = db.relationship('SqlThrottleRule', backref=db.backref('runs', lazy=True))

    def snapshot(self):
        if not self.snapshot_json:
            return {}
        try:
            return json.loads(self.snapshot_json)
        except (TypeError, ValueError):
            return {}

    def set_snapshot(self, payload):
        self.snapshot_json = json.dumps(payload or {}, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule.rule_name if self.rule else None,
            'status': self.status,
            'sample_started_at': self.sample_started_at.strftime('%Y-%m-%d %H:%M:%S') if self.sample_started_at else None,
            'sample_finished_at': self.sample_finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.sample_finished_at else None,
            'total_session_count': self.total_session_count,
            'candidate_fingerprint_count': self.candidate_fingerprint_count,
            'hit_fingerprint_count': self.hit_fingerprint_count,
            'kill_attempt_count': self.kill_attempt_count,
            'kill_success_count': self.kill_success_count,
            'dry_run': bool(self.dry_run),
            'error_message': self.error_message,
            'snapshot_json': self.snapshot(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
