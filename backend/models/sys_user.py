from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class SysUser(db.Model):
    __tablename__ = 'sys_user'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    employee_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(64), nullable=False)
    department = db.Column(db.String(128), nullable=False)
    role_code = db.Column(db.String(16), nullable=False, default='user')
    status = db.Column(db.String(16), nullable=False, default='enabled')
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(64), nullable=True)
    created_by = db.Column(db.BigInteger, nullable=True)
    updated_by = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_no': self.employee_no,
            'real_name': self.real_name,
            'department': self.department,
            'role_code': self.role_code,
            'status': self.status,
            'last_login_at': self.last_login_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_login_at else None,
            'last_login_ip': self.last_login_ip,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
