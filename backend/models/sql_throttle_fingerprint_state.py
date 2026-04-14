from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class SqlThrottleFingerprintState(db.Model):
    __tablename__ = 'sql_throttle_fingerprint_state'
    __table_args__ = (
        db.UniqueConstraint('rule_id', 'fingerprint_hash', name='uq_sql_throttle_rule_fingerprint_hash'),
    )

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    rule_id = db.Column(db.BigInteger, db.ForeignKey('sql_throttle_rule.id'), nullable=False)
    fingerprint_hash = db.Column(db.String(64), nullable=False)
    fingerprint = db.Column(db.Text, nullable=False)
    consecutive_hit_count = db.Column(db.Integer, nullable=False, default=0)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    last_hit_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    rule = db.relationship('SqlThrottleRule', backref=db.backref('fingerprint_states', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'fingerprint_hash': self.fingerprint_hash,
            'fingerprint': self.fingerprint,
            'consecutive_hit_count': self.consecutive_hit_count,
            'last_seen_at': self.last_seen_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_seen_at else None,
            'last_hit_at': self.last_hit_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_hit_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
