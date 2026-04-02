from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class UserConnectionPermission(db.Model):
    __tablename__ = 'sys_user_connection_permission'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'connection_id', name='uq_user_connection_permission'),
    )

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('sys_user.id'), nullable=False)
    connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='enabled')
    granted_by = db.Column(db.BigInteger, nullable=True)
    granted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    remark = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
