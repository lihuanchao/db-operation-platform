from datetime import datetime

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models.login_log import LoginLog
from models.sys_user import SysUser


class AuthService:
    ADMIN_MENU = [
        {'path': '/optimization-tasks', 'label': 'SQL优化建议'},
        {'path': '/slow-sqls', 'label': '慢SQL列表'},
        {'path': '/connections', 'label': '连接管理'},
        {'path': '/archive-tasks', 'label': '归档任务'},
        {'path': '/execution-logs', 'label': '执行日志'},
        {'path': '/users', 'label': '用户管理'},
        {'path': '/roles', 'label': '角色管理'},
        {'path': '/permissions', 'label': '权限管理'},
    ]
    USER_MENU = [
        {'path': '/optimization-tasks', 'label': 'SQL优化建议'},
        {'path': '/slow-sqls', 'label': '慢SQL列表'},
    ]

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password_hash, password):
        return check_password_hash(password_hash, password)

    @classmethod
    def login(cls, employee_no, password, ip, user_agent):
        user = SysUser.query.filter_by(employee_no=employee_no, deleted_at=None).first()
        if not user or not cls.verify_password(user.password_hash, password):
            cls.record_login(user.id if user else None, employee_no, 'failed', 'invalid_credentials', ip, user_agent)
            return None, ('工号或密码错误', 401)

        if user.status != 'enabled':
            cls.record_login(user.id, employee_no, 'failed', 'disabled', ip, user_agent)
            return None, ('账号已被禁用', 403)

        user.last_login_at = datetime.now()
        user.last_login_ip = ip
        session['user_id'] = user.id
        session['employee_no'] = user.employee_no
        session['role_code'] = user.role_code

        db.session.add(user)
        db.session.commit()
        cls.record_login(user.id, employee_no, 'success', None, ip, user_agent)
        return cls.build_auth_payload(user), None

    @staticmethod
    def logout():
        session.clear()

    @staticmethod
    def current_user():
        user_id = session.get('user_id')
        if not user_id:
            return None
        return SysUser.query.filter_by(id=user_id, deleted_at=None).first()

    @classmethod
    def build_auth_payload(cls, user):
        return {
            'user': user.to_dict(),
            'menus': cls.ADMIN_MENU if user.role_code == 'admin' else cls.USER_MENU,
        }

    @staticmethod
    def record_login(user_id, employee_no, result, reason, ip, user_agent):
        db.session.add(LoginLog(
            user_id=user_id,
            employee_no=employee_no,
            login_result=result,
            failure_reason=reason,
            login_ip=ip,
            user_agent=user_agent,
        ))
        db.session.commit()
