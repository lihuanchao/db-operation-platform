from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class LoginLog(db.Model):
    __tablename__ = 'sys_login_log'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=True)
    employee_no = db.Column(db.String(32), nullable=False)
    login_result = db.Column(db.String(16), nullable=False)
    failure_reason = db.Column(db.String(255), nullable=True)
    login_ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
