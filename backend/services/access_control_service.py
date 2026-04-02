from functools import wraps

from flask import jsonify

from models.db_connection import DbConnection
from models.user_connection_permission import UserConnectionPermission
from services.auth_service import AuthService


class AccessControlService:
    @staticmethod
    def authorized_connection_ids(user):
        if user.role_code == 'admin':
            return None

        rows = UserConnectionPermission.query.filter_by(
            user_id=user.id,
            status='enabled'
        ).all()
        return [row.connection_id for row in rows]

    @classmethod
    def authorized_manage_hosts(cls, user):
        if user.role_code == 'admin':
            return None

        connection_ids = cls.authorized_connection_ids(user)
        if not connection_ids:
            return []

        connections = DbConnection.query.filter(
            DbConnection.is_enabled != 0,
            DbConnection.id.in_(connection_ids)
        ).all()
        return [connection.manage_host for connection in connections if connection.manage_host]

    @classmethod
    def ensure_connection_access(cls, user, connection_id):
        authorized_ids = cls.authorized_connection_ids(user)
        if authorized_ids is None:
            return
        if connection_id not in authorized_ids:
            raise PermissionError('无连接权限')


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = AuthService.current_user()
        if not user or user.status != 'enabled':
            return jsonify({'success': False, 'error': '未登录'}), 401
        return view_func(user, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(current_user, *args, **kwargs):
        if current_user.role_code != 'admin':
            return jsonify({'success': False, 'error': '无权限访问'}), 403
        return view_func(current_user, *args, **kwargs)

    return wrapper
