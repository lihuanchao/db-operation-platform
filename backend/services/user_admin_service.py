from datetime import datetime

from extensions import db
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission
from services.auth_service import AuthService


class UserAdminService:
    FIXED_ROLES = [
        {
            'code': 'admin',
            'name': '管理员',
            'pages': ['全部页面'],
            'data_scope': '全部连接、全部数据',
        },
        {
            'code': 'user',
            'name': '普通用户',
            'pages': ['SQL优化', 'SQL巡检'],
            'data_scope': '仅授权连接；SQL优化仅自己创建；慢SQL不按创建人限制',
        },
    ]
    VALID_ROLES = {'admin', 'user'}
    VALID_STATUSES = {'enabled', 'disabled'}

    @staticmethod
    def list_users():
        return [
            user.to_dict()
            for user in SysUser.query.filter_by(deleted_at=None).order_by(SysUser.created_at.desc()).all()
        ]

    @classmethod
    def create_user(cls, payload, operator_id):
        employee_no = (payload.get('employee_no') or '').strip()
        password = payload.get('password') or ''
        real_name = (payload.get('real_name') or '').strip()
        department = (payload.get('department') or '').strip()
        role_code = payload.get('role_code') or 'user'
        status = payload.get('status') or 'enabled'

        if not employee_no or not password or not real_name or not department:
            raise ValueError('用户信息不完整')
        cls._validate_role_and_status(role_code, status)

        existing = SysUser.query.filter_by(employee_no=employee_no, deleted_at=None).first()
        if existing:
            raise ValueError('工号已存在')

        user = SysUser(
            employee_no=employee_no,
            password_hash=AuthService.hash_password(password),
            real_name=real_name,
            department=department,
            role_code=role_code,
            status=status,
            created_by=operator_id,
            updated_by=operator_id,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def update_user(cls, user_id, payload, operator_id):
        user = cls._get_user(user_id)
        role_code = payload.get('role_code') or user.role_code
        status = payload.get('status') or user.status
        cls._validate_role_and_status(role_code, status)

        user.real_name = (payload.get('real_name') or user.real_name).strip()
        user.department = (payload.get('department') or user.department).strip()
        user.role_code = role_code
        user.status = status
        user.updated_by = operator_id
        db.session.commit()
        return user

    @classmethod
    def update_status(cls, user_id, status, operator_id):
        cls._validate_role_and_status('user', status)
        user = cls._get_user(user_id)
        user.status = status
        user.updated_by = operator_id
        db.session.commit()
        return user

    @classmethod
    def reset_password(cls, user_id, password, operator_id):
        if not password:
            raise ValueError('密码不能为空')
        user = cls._get_user(user_id)
        user.password_hash = AuthService.hash_password(password)
        user.updated_by = operator_id
        db.session.commit()
        return user

    @classmethod
    def soft_delete_user(cls, user_id, operator_id):
        user = cls._get_user(user_id)
        user.deleted_at = datetime.now()
        user.status = 'disabled'
        user.updated_by = operator_id
        db.session.commit()

    @classmethod
    def replace_connection_permissions(cls, user_id, connection_ids, operator_id):
        cls._get_user(user_id)
        normalized_ids = sorted({int(connection_id) for connection_id in (connection_ids or [])})
        UserConnectionPermission.query.filter_by(user_id=user_id).delete()
        for connection_id in normalized_ids:
            db.session.add(UserConnectionPermission(
                user_id=user_id,
                connection_id=connection_id,
                status='enabled',
                granted_by=operator_id,
            ))
        db.session.commit()
        return normalized_ids

    @staticmethod
    def list_connection_permissions(user_id):
        items = UserConnectionPermission.query.filter_by(
            user_id=user_id,
            status='enabled'
        ).order_by(UserConnectionPermission.connection_id.asc()).all()
        return [item.connection_id for item in items]

    @classmethod
    def _get_user(cls, user_id):
        user = SysUser.query.filter_by(id=user_id, deleted_at=None).first()
        if not user:
            raise LookupError('用户不存在')
        return user

    @classmethod
    def _validate_role_and_status(cls, role_code, status):
        if role_code not in cls.VALID_ROLES:
            raise ValueError('角色不存在')
        if status not in cls.VALID_STATUSES:
            raise ValueError('状态不合法')
