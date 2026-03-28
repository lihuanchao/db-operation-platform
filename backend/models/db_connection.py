from datetime import datetime
from extensions import db
from utils.encryption import encrypt_password, decrypt_password


class DbConnection(db.Model):
    __tablename__ = 'db_connection'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='连接ID')
    connection_name = db.Column(db.String(100), nullable=False, comment='连接名称')
    host = db.Column(db.String(100), nullable=False, comment='数据库IP地址')
    manage_host = db.Column(db.String(100), nullable=True, comment='管理IP地址')
    port = db.Column(db.Integer, nullable=False, default=3306, comment='端口号')
    username = db.Column(db.String(100), nullable=False, comment='用户名')
    _password = db.Column('password', db.String(500), nullable=False, comment='加密后的密码')
    is_enabled = db.Column(db.Integer, nullable=False, default=1, comment='是否启用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    @property
    def password(self):
        """获取解密后的密码"""
        if self._password:
            try:
                return decrypt_password(self._password)
            except:
                return ''
        return ''

    @password.setter
    def password(self, value):
        """设置密码，自动加密"""
        if value:
            self._password = encrypt_password(value)
        else:
            self._password = ''

    def to_dict(self):
        """转换为字典（不包含密码）"""
        return {
            'id': self.id,
            'connection_name': self.connection_name,
            'host': self.host,
            'manage_host': self.manage_host,
            'port': self.port,
            'username': self.username,
            'is_enabled': bool(self.is_enabled),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def get_full_password(self):
        """获取解密后的密码（用于连接测试）"""
        return self.password