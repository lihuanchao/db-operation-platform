# 用户登录、角色与权限功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有数据库运维系统新增工号密码登录、固定角色、页面权限、连接授权、用户管理，并将权限规则接入 SQL优化建议 与 慢SQL列表。

**Architecture:** 后端继续沿用当前 Flask 单应用结构，在 `backend/app.py` 上增加认证与管理接口，把可复用的认证、授权、用户管理、慢 SQL 查询过滤逻辑下沉到 service 文件，并通过 `HttpOnly Cookie Session` 维持登录态。前端继续使用 Vue 3 + Pinia + Vue Router，在现有页面基础上补登录页、管理员页面、认证 store、路由守卫和动态菜单；普通用户的数据访问范围由后端最终裁剪，前端只负责展示和跳转控制。

**Tech Stack:** Flask, Flask-SQLAlchemy, SQLAlchemy, unittest, Vue 3, Pinia, Vue Router, Element Plus, Axios, Vitest, Vue Test Utils

---

## File Structure

### Backend

- Create: `backend/models/sys_user.py`
- Create: `backend/models/user_connection_permission.py`
- Create: `backend/models/login_log.py`
- Create: `backend/services/schema_migration_service.py`
- Create: `backend/services/auth_service.py`
- Create: `backend/services/access_control_service.py`
- Create: `backend/services/user_admin_service.py`
- Create: `backend/services/slow_sql_query_service.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/models/optimization_task.py`
- Modify: `backend/init_db.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_schema_migration_service.py`
- Test: `backend/tests/test_auth_api.py`
- Test: `backend/tests/test_admin_user_api.py`
- Test: `backend/tests/test_optimization_task_permissions.py`
- Test: `backend/tests/test_slow_sql_query_service.py`

### Frontend

- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/stores/index.ts`
- Create: `frontend/src/auth/access.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/userAdmin.ts`
- Create: `frontend/src/api/permissionAdmin.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/stores/userAdmin.ts`
- Create: `frontend/src/stores/permissionAdmin.ts`
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/UserManagement.vue`
- Create: `frontend/src/views/RoleManagement.vue`
- Create: `frontend/src/views/PermissionManagement.vue`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/api/request.ts`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/views/OptimizationTaskCreateSql.vue`
- Modify: `frontend/src/views/OptimizationTaskCreateMyBatis.vue`
- Test: `frontend/src/auth/access.spec.ts`
- Test: `frontend/src/stores/auth.spec.ts`
- Test: `frontend/src/stores/userAdmin.spec.ts`

## Task 1: Add Auth Schema Models And Idempotent Schema Migration

**Files:**
- Create: `backend/models/sys_user.py`
- Create: `backend/models/user_connection_permission.py`
- Create: `backend/models/login_log.py`
- Create: `backend/services/schema_migration_service.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/models/optimization_task.py`
- Modify: `backend/init_db.py`
- Test: `backend/tests/test_schema_migration_service.py`

- [ ] **Step 1: Write the failing schema migration test**

```python
import unittest
from sqlalchemy import inspect

from app import app
from extensions import db
from services.schema_migration_service import SchemaMigrationService


class SchemaMigrationServiceTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://'
        )
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_ensure_auth_schema_creates_tables_and_columns(self):
        SchemaMigrationService.ensure_auth_schema()

        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        self.assertIn('sys_user', table_names)
        self.assertIn('sys_user_connection_permission', table_names)
        self.assertIn('sys_login_log', table_names)

        optimization_columns = {
            column['name'] for column in inspector.get_columns('optimization_task')
        }
        self.assertIn('creator_user_id', optimization_columns)
        self.assertIn('creator_employee_no', optimization_columns)
        self.assertIn('connection_id', optimization_columns)
        self.assertIn('database_name', optimization_columns)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify the current code fails**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_schema_migration_service -v
```

Expected: FAIL with `ModuleNotFoundError` for `tests.test_schema_migration_service` or `ImportError` for `SchemaMigrationService`.

- [ ] **Step 3: Add the new models, migration service, and optimization task ownership fields**

`backend/models/sys_user.py`

```python
from datetime import datetime

from extensions import db


class SysUser(db.Model):
    __tablename__ = 'sys_user'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
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
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
```

`backend/models/user_connection_permission.py`

```python
from datetime import datetime

from extensions import db


class UserConnectionPermission(db.Model):
    __tablename__ = 'sys_user_connection_permission'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'connection_id', name='uq_user_connection_permission'),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('sys_user.id'), nullable=False)
    connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='enabled')
    granted_by = db.Column(db.BigInteger, nullable=True)
    granted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    remark = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
```

`backend/models/login_log.py`

```python
from datetime import datetime

from extensions import db


class LoginLog(db.Model):
    __tablename__ = 'sys_login_log'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=True)
    employee_no = db.Column(db.String(32), nullable=False)
    login_result = db.Column(db.String(16), nullable=False)
    failure_reason = db.Column(db.String(255), nullable=True)
    login_ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
```

`backend/services/schema_migration_service.py`

```python
from sqlalchemy import inspect, text

from extensions import db
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission
from models.login_log import LoginLog


class SchemaMigrationService:
    REQUIRED_OPTIMIZATION_COLUMNS = {
        'creator_user_id': 'ALTER TABLE optimization_task ADD COLUMN creator_user_id BIGINT NULL',
        'creator_employee_no': 'ALTER TABLE optimization_task ADD COLUMN creator_employee_no VARCHAR(32) NULL',
        'connection_id': 'ALTER TABLE optimization_task ADD COLUMN connection_id BIGINT NULL'
    }

    @classmethod
    def ensure_auth_schema(cls):
        SysUser.__table__.create(bind=db.engine, checkfirst=True)
        UserConnectionPermission.__table__.create(bind=db.engine, checkfirst=True)
        LoginLog.__table__.create(bind=db.engine, checkfirst=True)

        inspector = inspect(db.engine)
        existing_columns = {
            column['name'] for column in inspector.get_columns('optimization_task')
        }
        for name, ddl in cls.REQUIRED_OPTIMIZATION_COLUMNS.items():
            if name not in existing_columns:
                db.session.execute(text(ddl))
        db.session.commit()
```

`backend/models/optimization_task.py`

```python
    creator_user_id = db.Column(db.BigInteger, nullable=True, comment='创建人用户ID')
    creator_employee_no = db.Column(db.String(32), nullable=True, comment='创建人工号')
    connection_id = db.Column(db.BigInteger, nullable=True, comment='权限过滤使用的连接ID')
```

`backend/models/__init__.py`

```python
from .sys_user import SysUser
from .user_connection_permission import UserConnectionPermission
from .login_log import LoginLog
```

`backend/init_db.py`

```python
from services.schema_migration_service import SchemaMigrationService


def init_db():
    with app.app_context():
        db.create_all()
        SchemaMigrationService.ensure_auth_schema()
```

- [ ] **Step 4: Run the schema migration test and the existing optimization task test**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_schema_migration_service tests.test_optimization_task_service -v
```

Expected: PASS for both test modules.

- [ ] **Step 5: Commit the schema task**

```bash
git add backend/models/sys_user.py backend/models/user_connection_permission.py backend/models/login_log.py backend/services/schema_migration_service.py backend/models/__init__.py backend/models/optimization_task.py backend/init_db.py backend/tests/test_schema_migration_service.py
git commit -m "feat: add auth schema and migration service"
```

## Task 2: Implement Authentication Service And Session APIs

**Files:**
- Create: `backend/services/auth_service.py`
- Create: `backend/services/access_control_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Write the failing authentication API test**

```python
import unittest

from app import app
from extensions import db
from models.sys_user import SysUser
from services.auth_service import AuthService


class AuthApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SECRET_KEY='test-secret'
        )
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        admin = SysUser(
            employee_no='A1001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled'
        )
        disabled_user = SysUser(
            employee_no='U1001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='禁用用户',
            department='研发',
            role_code='user',
            status='disabled'
        )
        db.session.add_all([admin, disabled_user])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_login_me_logout_flow(self):
        response = self.client.post('/api/auth/login', json={
            'employee_no': 'A1001',
            'password': 'Passw0rd!'
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['user']['role_code'], 'admin')

        me_response = self.client.get('/api/auth/me')
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.get_json()['data']['user']['employee_no'], 'A1001')

        logout_response = self.client.post('/api/auth/logout')
        self.assertEqual(logout_response.status_code, 200)

        me_after_logout = self.client.get('/api/auth/me')
        self.assertEqual(me_after_logout.status_code, 401)

    def test_disabled_user_cannot_login(self):
        response = self.client.post('/api/auth/login', json={
            'employee_no': 'U1001',
            'password': 'Passw0rd!'
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error'], '账号已被禁用')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the auth API test to verify it fails**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_auth_api -v
```

Expected: FAIL with `ImportError` for `AuthService` or missing `/api/auth/*` routes.

- [ ] **Step 3: Implement password hashing, session loading, auth decorators, and `/api/auth/*` routes**

`backend/services/auth_service.py`

```python
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
        {'path': '/permissions', 'label': '权限管理'}
    ]
    USER_MENU = [
        {'path': '/optimization-tasks', 'label': 'SQL优化建议'},
        {'path': '/slow-sqls', 'label': '慢SQL列表'}
    ]

    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)

    @classmethod
    def login(cls, employee_no: str, password: str, ip: str, user_agent: str):
        user = SysUser.query.filter_by(employee_no=employee_no, deleted_at=None).first()
        if not user or not cls.verify_password(user.password_hash, password):
            cls.record_login(None, employee_no, 'failed', 'invalid_credentials', ip, user_agent)
            return None, ('工号或密码错误', 401)
        if user.status != 'enabled':
            cls.record_login(user.id, employee_no, 'failed', 'disabled', ip, user_agent)
            return None, ('账号已被禁用', 403)

        user.last_login_at = datetime.now()
        user.last_login_ip = ip
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['employee_no'] = user.employee_no
        session['role_code'] = user.role_code

        cls.record_login(user.id, employee_no, 'success', None, ip, user_agent)
        return cls.build_auth_payload(user), None

    @classmethod
    def logout(cls):
        session.clear()

    @classmethod
    def current_user(cls):
        user_id = session.get('user_id')
        if not user_id:
            return None
        return SysUser.query.filter_by(id=user_id, deleted_at=None).first()

    @classmethod
    def build_auth_payload(cls, user: SysUser):
        return {
            'user': user.to_dict(),
            'menus': cls.ADMIN_MENU if user.role_code == 'admin' else cls.USER_MENU
        }

    @staticmethod
    def record_login(user_id, employee_no, result, reason, ip, user_agent):
        db.session.add(LoginLog(
            user_id=user_id,
            employee_no=employee_no,
            login_result=result,
            failure_reason=reason,
            login_ip=ip,
            user_agent=user_agent
        ))
        db.session.commit()
```

`backend/services/access_control_service.py`

```python
from functools import wraps

from flask import jsonify

from services.auth_service import AuthService


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
```

`backend/app.py`

```python
app = Flask(__name__)
app.config.from_object(Config)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)
CORS(app, supports_credentials=True)

from flask import session
from services.auth_service import AuthService
from services.access_control_service import login_required, admin_required


@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    employee_no = (payload.get('employee_no') or '').strip()
    password = payload.get('password') or ''
    if not employee_no or not password:
        return error_response('工号和密码不能为空', 400)

    data, error = AuthService.login(
        employee_no=employee_no,
        password=password,
        ip=request.headers.get('X-Forwarded-For', request.remote_addr),
        user_agent=request.headers.get('User-Agent', '')
    )
    if error:
        message, status_code = error
        return error_response(message, status_code)
    return success_response(data)


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout(current_user):
    AuthService.logout()
    return success_response({'logged_out': True})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def me(current_user):
    return success_response(AuthService.build_auth_payload(current_user))
```

- [ ] **Step 4: Run the authentication tests**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_auth_api -v
```

Expected: PASS with `test_login_me_logout_flow` and `test_disabled_user_cannot_login`.

- [ ] **Step 5: Commit the authentication task**

```bash
git add backend/services/auth_service.py backend/services/access_control_service.py backend/app.py backend/tests/test_auth_api.py
git commit -m "feat: add session auth APIs"
```

## Task 3: Implement Admin User Management, Role Read API, And Connection Authorization APIs

**Files:**
- Create: `backend/services/user_admin_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_admin_user_api.py`

- [ ] **Step 1: Write the failing admin user and permission API tests**

```python
import unittest

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.sys_user import SysUser
from services.auth_service import AuthService


class AdminUserApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://', SECRET_KEY='admin-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        self.admin = SysUser(
            employee_no='A1001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled'
        )
        self.user = SysUser(
            employee_no='U1002',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='普通用户',
            department='研发',
            role_code='user',
            status='enabled'
        )
        self.connection = DbConnection(
            connection_name='测试连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1
        )
        db.session.add_all([self.admin, self.user, self.connection])
        db.session.commit()
        self.client.post('/api/auth/login', json={'employee_no': 'A1001', 'password': 'Passw0rd!'})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_create_disable_and_list_users(self):
        create_response = self.client.post('/api/admin/users', json={
            'employee_no': 'U2001',
            'password': 'InitPass123',
            'real_name': '新用户',
            'department': '测试部',
            'role_code': 'user',
            'status': 'enabled'
        })
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get('/api/admin/users')
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(any(item['employee_no'] == 'U2001' for item in list_response.get_json()['data']['items']))

        created_user_id = next(
            item['id'] for item in list_response.get_json()['data']['items']
            if item['employee_no'] == 'U2001'
        )
        disable_response = self.client.put(
            f'/api/admin/users/{created_user_id}/status',
            json={'status': 'disabled'}
        )
        self.assertEqual(disable_response.status_code, 200)
        self.assertEqual(disable_response.get_json()['data']['status'], 'disabled')

    def test_update_reset_password_and_delete_user(self):
        update_response = self.client.put(f'/api/admin/users/{self.user.id}', json={
            'real_name': '普通用户-已修改',
            'department': '数据平台',
            'role_code': 'user',
            'status': 'enabled'
        })
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.get_json()['data']['real_name'], '普通用户-已修改')

        reset_response = self.client.put(f'/api/admin/users/{self.user.id}/reset-password', json={
            'password': 'NewPass123'
        })
        self.assertEqual(reset_response.status_code, 200)

        delete_response = self.client.delete(f'/api/admin/users/{self.user.id}')
        self.assertEqual(delete_response.status_code, 200)

        list_response = self.client.get('/api/admin/users')
        employee_nos = [item['employee_no'] for item in list_response.get_json()['data']['items']]
        self.assertNotIn('U1002', employee_nos)

    def test_save_connection_permissions(self):
        response = self.client.put(f'/api/admin/user-connection-permissions/{self.user.id}', json={
            'connection_ids': [self.connection.id]
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['data']['connection_ids'], [self.connection.id])

    def test_roles_api_returns_fixed_roles(self):
        response = self.client.get('/api/admin/roles')
        self.assertEqual(response.status_code, 200)
        roles = response.get_json()['data']
        self.assertEqual([role['code'] for role in roles], ['admin', 'user'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the admin API tests to verify they fail**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_admin_user_api -v
```

Expected: FAIL because `/api/admin/users`, `/api/admin/roles`, and `/api/admin/user-connection-permissions/*` do not exist.

- [ ] **Step 3: Implement admin services and endpoints**

`backend/services/user_admin_service.py`

```python
from extensions import db
from models.db_connection import DbConnection
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission
from services.auth_service import AuthService


class UserAdminService:
    FIXED_ROLES = [
        {
            'code': 'admin',
            'name': '管理员',
            'pages': ['全部页面'],
            'data_scope': '全部连接、全部数据'
        },
        {
            'code': 'user',
            'name': '普通用户',
            'pages': ['SQL优化建议', '慢SQL列表'],
            'data_scope': '仅授权连接；SQL优化建议仅自己创建；慢SQL不按创建人限制'
        }
    ]

    @staticmethod
    def list_users():
        return [user.to_dict() for user in SysUser.query.filter_by(deleted_at=None).order_by(SysUser.created_at.desc()).all()]

    @staticmethod
    def create_user(payload, operator_id):
        existing = SysUser.query.filter_by(employee_no=payload['employee_no'].strip(), deleted_at=None).first()
        if existing:
            raise ValueError('工号已存在')
        user = SysUser(
            employee_no=payload['employee_no'].strip(),
            password_hash=AuthService.hash_password(payload['password']),
            real_name=payload['real_name'].strip(),
            department=payload['department'].strip(),
            role_code=payload['role_code'],
            status=payload['status'],
            created_by=operator_id,
            updated_by=operator_id
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_user(user_id, payload, operator_id):
        user = SysUser.query.filter_by(id=user_id, deleted_at=None).first_or_404()
        user.real_name = payload['real_name'].strip()
        user.department = payload['department'].strip()
        user.role_code = payload['role_code']
        user.status = payload['status']
        user.updated_by = operator_id
        db.session.commit()
        return user

    @staticmethod
    def update_status(user_id, status, operator_id):
        user = SysUser.query.filter_by(id=user_id, deleted_at=None).first_or_404()
        user.status = status
        user.updated_by = operator_id
        db.session.commit()
        return user

    @staticmethod
    def reset_password(user_id, password, operator_id):
        user = SysUser.query.filter_by(id=user_id, deleted_at=None).first_or_404()
        user.password_hash = AuthService.hash_password(password)
        user.updated_by = operator_id
        db.session.commit()
        return user

    @staticmethod
    def soft_delete_user(user_id, operator_id):
        user = SysUser.query.filter_by(id=user_id, deleted_at=None).first_or_404()
        user.deleted_at = db.func.now()
        user.updated_by = operator_id
        db.session.commit()

    @staticmethod
    def replace_connection_permissions(user_id, connection_ids, operator_id):
        UserConnectionPermission.query.filter_by(user_id=user_id).delete()
        for connection_id in connection_ids:
            db.session.add(UserConnectionPermission(
                user_id=user_id,
                connection_id=connection_id,
                status='enabled',
                granted_by=operator_id
            ))
        db.session.commit()
        return connection_ids

    @staticmethod
    def list_connection_permissions(user_id):
        items = UserConnectionPermission.query.filter_by(user_id=user_id, status='enabled').all()
        return [item.connection_id for item in items]
```

`backend/app.py`

```python
from services.user_admin_service import UserAdminService


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users(current_user):
    return success_response({'items': UserAdminService.list_users()})


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user(current_user):
    payload = request.get_json(silent=True) or {}
    try:
        user = UserAdminService.create_user(payload, current_user.id)
    except ValueError as exc:
        return error_response(str(exc), 409)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    user = UserAdminService.update_user(user_id, payload, current_user.id)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    user = UserAdminService.update_status(user_id, payload['status'], current_user.id)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['PUT'])
@admin_required
def reset_user_password(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    user = UserAdminService.reset_password(user_id, payload['password'], current_user.id)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    UserAdminService.soft_delete_user(user_id, current_user.id)
    return success_response({'deleted': True})


@app.route('/api/admin/roles', methods=['GET'])
@admin_required
def list_roles(current_user):
    return success_response(UserAdminService.FIXED_ROLES)


@app.route('/api/admin/user-connection-permissions/<int:user_id>', methods=['GET'])
@admin_required
def get_user_connection_permissions(current_user, user_id):
    return success_response({'connection_ids': UserAdminService.list_connection_permissions(user_id)})


@app.route('/api/admin/user-connection-permissions/<int:user_id>', methods=['PUT'])
@admin_required
def replace_user_connection_permissions(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    connection_ids = UserAdminService.replace_connection_permissions(
        user_id,
        payload.get('connection_ids', []),
        current_user.id
    )
    return success_response({'connection_ids': connection_ids})


@app.route('/api/auth/connections', methods=['GET'])
@login_required
def list_authorized_connections(current_user):
    if current_user.role_code == 'admin':
        connections = DbConnection.query.filter(DbConnection.is_enabled != 0).all()
    else:
        connection_ids = UserAdminService.list_connection_permissions(current_user.id)
        connections = DbConnection.query.filter(
            DbConnection.is_enabled != 0,
            DbConnection.id.in_(connection_ids)
        ).all()
    return success_response({'items': [item.to_dict() for item in connections]})
```

- [ ] **Step 4: Run the admin API tests**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_admin_user_api -v
```

Expected: PASS for user新增/编辑/禁用/重置密码/删除、固定角色 API、以及连接权限保存。

- [ ] **Step 5: Commit the admin API task**

```bash
git add backend/services/user_admin_service.py backend/app.py backend/tests/test_admin_user_api.py
git commit -m "feat: add admin user and permission APIs"
```

## Task 4: Enforce SQL Optimization Task Ownership And Connection Permissions

**Files:**
- Modify: `backend/services/access_control_service.py`
- Modify: `backend/services/optimization_task_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_optimization_task_permissions.py`

- [ ] **Step 1: Write the failing optimization permission tests**

```python
import unittest

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.optimization_task import OptimizationTask
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission
from services.auth_service import AuthService


class OptimizationTaskPermissionTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://', SECRET_KEY='opt-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        self.admin = SysUser(employee_no='A1', password_hash=AuthService.hash_password('Passw0rd!'), real_name='管理员', department='DBA', role_code='admin', status='enabled')
        self.user = SysUser(employee_no='U1', password_hash=AuthService.hash_password('Passw0rd!'), real_name='普通用户', department='研发', role_code='user', status='enabled')
        self.other = SysUser(employee_no='U2', password_hash=AuthService.hash_password('Passw0rd!'), real_name='其他用户', department='研发', role_code='user', status='enabled')
        self.connection = DbConnection(connection_name='授权连接', host='10.0.0.10', manage_host='10.0.0.11', port=3306, username='root', password='secret', is_enabled=1)
        db.session.add_all([self.admin, self.user, self.other, self.connection])
        db.session.commit()
        db.session.add(UserConnectionPermission(user_id=self.user.id, connection_id=self.connection.id, status='enabled'))
        db.session.add(OptimizationTask(
            task_type='sql',
            object_content='select 1',
            object_preview='select 1',
            db_connection_id=self.connection.id,
            connection_id=self.connection.id,
            database_name='demo',
            database_host='10.0.0.10',
            creator_user_id=self.other.id,
            creator_employee_no=self.other.employee_no,
            status='completed',
            progress=100
        ))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_normal_user_only_sees_own_tasks(self):
        self.client.post('/api/auth/login', json={'employee_no': 'U1', 'password': 'Passw0rd!'})
        response = self.client.get('/api/optimization-tasks?page=1&per_page=10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data']['items'], [])

    def test_normal_user_cannot_view_other_user_task_detail(self):
        task_id = OptimizationTask.query.filter_by(creator_user_id=self.other.id).first().id
        self.client.post('/api/auth/login', json={'employee_no': 'U1', 'password': 'Passw0rd!'})
        response = self.client.get(f'/api/optimization-tasks/{task_id}')
        self.assertEqual(response.status_code, 404)

    def test_normal_user_cannot_create_task_for_unauthorized_connection(self):
        unauthorized = DbConnection(connection_name='未授权连接', host='10.0.0.20', manage_host='10.0.0.21', port=3306, username='root', password='secret', is_enabled=1)
        db.session.add(unauthorized)
        db.session.commit()
        self.client.post('/api/auth/login', json={'employee_no': 'U1', 'password': 'Passw0rd!'})
        response = self.client.post('/api/optimization-tasks/sql', json={
            'db_connection_id': unauthorized.id,
            'database_name': 'demo',
            'sql_text': 'select * from user'
        })
        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the optimization permission tests to verify they fail**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_optimization_task_permissions -v
```

Expected: FAIL because optimization task list/detail/create routes do not filter by current user or connection authorization.

- [ ] **Step 3: Add reusable connection authorization helpers and update optimization task endpoints**

`backend/services/access_control_service.py`

```python
from models.user_connection_permission import UserConnectionPermission


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
    def ensure_connection_access(cls, user, connection_id):
        authorized_ids = cls.authorized_connection_ids(user)
        if authorized_ids is None:
            return
        if connection_id not in authorized_ids:
            raise PermissionError('无连接权限')
```

`backend/services/optimization_task_service.py`

```python
from extensions import db
from models.db_connection import DbConnection


class OptimizationTaskService:
    @staticmethod
    def create_sql_task(payload, current_user):
        db_connection = DbConnection.query.get_or_404(payload['db_connection_id'])
        task = OptimizationTask(
            task_type='sql',
            object_content=payload['sql_text'],
            object_preview=payload['sql_text'][:255],
            db_connection_id=payload['db_connection_id'],
            connection_id=payload['db_connection_id'],
            database_name=payload['database_name'],
            database_host=db_connection.host,
            creator_user_id=current_user.id,
            creator_employee_no=current_user.employee_no,
            status='queued',
            progress=0
        )
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def create_mybatis_task(payload, current_user):
        db_connection = DbConnection.query.get_or_404(payload['db_connection_id'])
        task = OptimizationTask(
            task_type='mybatis',
            object_content=payload['xml_text'],
            object_preview=payload['xml_text'][:255],
            db_connection_id=payload['db_connection_id'],
            connection_id=payload['db_connection_id'],
            database_name=payload['database_name'],
            database_host=db_connection.host,
            creator_user_id=current_user.id,
            creator_employee_no=current_user.employee_no,
            status='queued',
            progress=0
        )
        db.session.add(task)
        db.session.commit()
        return task
```

`backend/app.py`

```python
from services.access_control_service import AccessControlService


@app.route('/api/optimization-tasks', methods=['GET'])
@login_required
def list_optimization_tasks(current_user):
    query = OptimizationTask.query.order_by(OptimizationTask.created_at.desc())
    if current_user.role_code != 'admin':
        authorized_ids = AccessControlService.authorized_connection_ids(current_user)
        query = query.filter(
            OptimizationTask.creator_user_id == current_user.id,
            OptimizationTask.connection_id.in_(authorized_ids or [-1])
        )
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return success_response({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page
    })


@app.route('/api/optimization-tasks/sql', methods=['POST'])
@login_required
def create_sql_optimization_task(current_user):
    payload = request.get_json(silent=True) or {}
    try:
        AccessControlService.ensure_connection_access(current_user, payload['db_connection_id'])
    except PermissionError:
        return error_response('无连接权限', 403)
    task = OptimizationTaskService.create_sql_task(payload, current_user)
    return success_response(task.to_dict())


@app.route('/api/optimization-tasks/mybatis', methods=['POST'])
@login_required
def create_mybatis_optimization_task(current_user):
    payload = request.get_json(silent=True) or {}
    try:
        AccessControlService.ensure_connection_access(current_user, payload['db_connection_id'])
    except PermissionError:
        return error_response('无连接权限', 403)
    task = OptimizationTaskService.create_mybatis_task(payload, current_user)
    return success_response(task.to_dict())


@app.route('/api/optimization-tasks/<int:task_id>', methods=['GET'])
@login_required
def get_optimization_task_detail(current_user, task_id):
    query = OptimizationTask.query.filter_by(id=task_id)
    if current_user.role_code != 'admin':
        authorized_ids = AccessControlService.authorized_connection_ids(current_user) or [-1]
        query = query.filter(
            OptimizationTask.creator_user_id == current_user.id,
            OptimizationTask.connection_id.in_(authorized_ids)
        )
    task = query.first()
    if not task:
        return error_response('未找到该优化任务', 404)
    return success_response(task.to_dict(include_content=True))
```

- [ ] **Step 4: Run the optimization permission tests and the existing optimization parser tests**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_optimization_task_permissions tests.test_optimization_task_service -v
```

Expected: PASS for both modules.

- [ ] **Step 5: Commit the optimization permission task**

```bash
git add backend/services/access_control_service.py backend/services/optimization_task_service.py backend/app.py backend/tests/test_optimization_task_permissions.py
git commit -m "feat: enforce optimization task permissions"
```

## Task 5: Move Slow SQL Query Building Into A Service And Apply Authorized Manage-Host Filtering

**Files:**
- Create: `backend/services/slow_sql_query_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_slow_sql_query_service.py`

- [ ] **Step 1: Write the failing slow SQL query service tests**

```python
import unittest

from services.slow_sql_query_service import SlowSqlQueryService


class SlowSqlQueryServiceTestCase(unittest.TestCase):
    def test_build_list_query_adds_manage_host_scope_for_normal_user(self):
        sql, params = SlowSqlQueryService.build_list_query(
            filters={'database_name': '', 'host': '', 'is_optimized': ''},
            allowed_hosts=['10.0.0.11', '10.0.0.21']
        )
        self.assertIn('c.host IN (:allowed_host_0, :allowed_host_1)', sql)
        self.assertEqual(params['allowed_host_0'], '10.0.0.11')
        self.assertEqual(params['allowed_host_1'], '10.0.0.21')

    def test_build_list_query_skips_manage_host_scope_for_admin(self):
        sql, params = SlowSqlQueryService.build_list_query(
            filters={'database_name': '', 'host': '', 'is_optimized': ''},
            allowed_hosts=None
        )
        self.assertNotIn('allowed_host_0', sql)
        self.assertNotIn('allowed_host_0', params)

    def test_build_detail_query_reuses_authorized_host_scope(self):
        sql, params = SlowSqlQueryService.build_detail_query('abc123', allowed_hosts=['10.0.0.11'])
        self.assertIn('a.checksum = :checksum', sql)
        self.assertIn('c.host IN (:allowed_host_0)', sql)
        self.assertEqual(params['checksum'], 'abc123')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the slow SQL query service test to verify it fails**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_slow_sql_query_service -v
```

Expected: FAIL with `ModuleNotFoundError` for `services.slow_sql_query_service`.

- [ ] **Step 3: Extract raw SQL building into a service and filter by authorized manage hosts**

`backend/services/slow_sql_query_service.py`

```python
class SlowSqlQueryService:
    BASE_SQL = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
    LEFT JOIN monitor_mysql_slow_query_optimized m ON a.checksum = m.checksum
WHERE
    c.host IS NOT NULL
    AND c.port IS NOT NULL
    AND c.is_delete != 1
    AND a.sample != 'commit'
    AND (b.db_max != 'information_schema' OR b.db_max IS NULL)
    AND b.user_max IS NOT NULL
"""

    @classmethod
    @staticmethod
    def build_host_scope(allowed_hosts):
        if allowed_hosts is None:
            return '', {}
        placeholders = ', '.join(f':allowed_host_{index}' for index, _ in enumerate(allowed_hosts or ['__empty__']))
        params = {f'allowed_host_{index}': host for index, host in enumerate(allowed_hosts or ['__empty__'])}
        return f' AND c.host IN ({placeholders})', params

    @classmethod
    def build_list_query(cls, filters, allowed_hosts=None):
        sql = cls.BASE_SQL
        host_scope_sql, host_scope_params = cls.build_host_scope(allowed_hosts)
        sql += host_scope_sql
        params = dict(host_scope_params)
        if filters.get('host'):
            sql += ' AND c.host = :host'
            params['host'] = filters['host']
        if filters.get('database_name'):
            sql += ' AND b.db_max = :database_name'
            params['database_name'] = filters['database_name']
        sql += ' GROUP BY a.checksum ORDER BY SUM(b.Query_time_sum) DESC'
        return sql, params

    @classmethod
    def build_detail_query(cls, checksum, allowed_hosts=None):
        host_scope_sql, host_scope_params = cls.build_host_scope(allowed_hosts)
        sql = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    b.user_max,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time,
    MAX(b.Query_time_max) AS max_time,
    MIN(b.Query_time_min) AS min_time,
    SUM(b.Query_time_sum) AS total_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE
    a.checksum = :checksum
""" + host_scope_sql + """
GROUP BY
    a.checksum
"""
        params = {'checksum': checksum, **host_scope_params}
        return sql, params
```

`backend/app.py`

```python
from services.slow_sql_query_service import SlowSqlQueryService


@app.route('/api/slow-sqls', methods=['GET'])
@login_required
def get_slow_sqls(current_user):
    filters = {
        'database_name': request.args.get('database_name', ''),
        'host': request.args.get('host', ''),
        'is_optimized': request.args.get('is_optimized', ''),
        'time_range': request.args.get('time_range', '')
    }
    allowed_hosts = None
    if current_user.role_code != 'admin':
        connection_ids = AccessControlService.authorized_connection_ids(current_user) or []
        connections = DbConnection.query.filter(DbConnection.id.in_(connection_ids)).all()
        allowed_hosts = [item.manage_host for item in connections if item.manage_host]

    sql_query, params = SlowSqlQueryService.build_list_query(filters, allowed_hosts=allowed_hosts)
```

`backend/app.py` slow SQL detail route update

```python
@app.route('/api/slow-sqls/<checksum>', methods=['GET'])
@login_required
def get_slow_sql_detail(current_user, checksum):
    allowed_hosts = None
    if current_user.role_code != 'admin':
        connection_ids = AccessControlService.authorized_connection_ids(current_user) or []
        connections = DbConnection.query.filter(DbConnection.id.in_(connection_ids)).all()
        allowed_hosts = [item.manage_host for item in connections if item.manage_host]

    sql_query, params = SlowSqlQueryService.build_detail_query(checksum, allowed_hosts=allowed_hosts)
    with db.engine.connect() as conn:
        result = conn.execute(text(sql_query), params)
        row = result.fetchone()
        if not row:
            return error_response('未找到该SQL记录', 404)
```

- [ ] **Step 4: Run the slow SQL service test and a targeted auth test**

Run:

```bash
cd backend && ../venv/bin/python -m unittest tests.test_slow_sql_query_service tests.test_auth_api -v
```

Expected: PASS for both modules.

- [ ] **Step 5: Commit the slow SQL authorization task**

```bash
git add backend/services/slow_sql_query_service.py backend/app.py backend/tests/test_slow_sql_query_service.py
git commit -m "feat: filter slow sql by authorized manage host"
```

## Task 6: Add Frontend Test Tooling And Pure Access-Control Helpers

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/auth/access.ts`
- Test: `frontend/src/auth/access.spec.ts`

- [ ] **Step 1: Write the failing frontend access helper test**

```ts
import { describe, expect, it } from 'vitest'
import { canAccessPath, getVisibleMenus } from './access'

describe('access helpers', () => {
  it('shows only optimization and slow sql for normal user', () => {
    const menus = getVisibleMenus('user').map((item) => item.path)
    expect(menus).toEqual(['/optimization-tasks', '/slow-sqls'])
  })

  it('allows normal user to access detail routes under allowed modules', () => {
    expect(canAccessPath('user', '/optimization-tasks/12')).toBe(true)
    expect(canAccessPath('user', '/slow-sql/abc123')).toBe(true)
  })

  it('blocks normal user from admin pages', () => {
    expect(canAccessPath('user', '/connections')).toBe(false)
    expect(canAccessPath('user', '/users')).toBe(false)
  })

  it('allows admin to access admin pages', () => {
    expect(canAccessPath('admin', '/permissions')).toBe(true)
  })
})
```

- [ ] **Step 2: Run the frontend test command to verify it fails**

Run:

```bash
cd frontend && npm run test -- --run src/auth/access.spec.ts
```

Expected: FAIL with `Missing script: "test"`.

- [ ] **Step 3: Add Vitest and implement the pure access helper**

`frontend/package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "devDependencies": {
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^26.0.0",
    "vitest": "^3.2.4"
  }
}
```

`frontend/vitest.config.ts`

```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts']
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
```

`frontend/src/test/setup.ts`

```ts
import { config } from '@vue/test-utils'

config.global.stubs = {
  'el-icon': true
}
```

`frontend/src/auth/access.ts`

```ts
export type RoleCode = 'admin' | 'user'

export interface MenuItem {
  path: string
  label: string
  roles: RoleCode[]
  matchPrefixes: string[]
}

export const MENU_ITEMS: MenuItem[] = [
  { path: '/optimization-tasks', label: 'SQL优化建议', roles: ['admin', 'user'], matchPrefixes: ['/optimization-tasks'] },
  { path: '/slow-sqls', label: '慢SQL列表', roles: ['admin', 'user'], matchPrefixes: ['/slow-sqls', '/slow-sql/'] },
  { path: '/connections', label: '连接管理', roles: ['admin'], matchPrefixes: ['/connections'] },
  { path: '/archive-tasks', label: '归档任务', roles: ['admin'], matchPrefixes: ['/archive-tasks'] },
  { path: '/execution-logs', label: '执行日志', roles: ['admin'], matchPrefixes: ['/execution-logs'] },
  { path: '/users', label: '用户管理', roles: ['admin'], matchPrefixes: ['/users'] },
  { path: '/roles', label: '角色管理', roles: ['admin'], matchPrefixes: ['/roles'] },
  { path: '/permissions', label: '权限管理', roles: ['admin'], matchPrefixes: ['/permissions'] }
]

export function getVisibleMenus(roleCode: RoleCode): MenuItem[] {
  return MENU_ITEMS.filter((item) => item.roles.includes(roleCode))
}

export function canAccessPath(roleCode: RoleCode, path: string): boolean {
  const matched = MENU_ITEMS.find((item) => item.matchPrefixes.some((prefix) => path === prefix || path.startsWith(prefix)))
  return matched ? matched.roles.includes(roleCode) : roleCode === 'admin'
}
```

- [ ] **Step 4: Run the frontend access helper test**

Run:

```bash
cd frontend && npm install && npm run test -- --run src/auth/access.spec.ts
```

Expected: PASS with 4 tests passed.

- [ ] **Step 5: Commit the frontend test harness task**

```bash
git add frontend/package.json frontend/vitest.config.ts frontend/src/test/setup.ts frontend/src/auth/access.ts frontend/src/auth/access.spec.ts
git commit -m "test: add frontend auth access test harness"
```

## Task 7: Add Frontend Auth Store, Login Page, Route Guards, And 401 Handling

**Files:**
- Create: `frontend/src/stores/index.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/api/request.ts`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Modify: `frontend/src/types/index.ts`
- Test: `frontend/src/stores/auth.spec.ts`

- [ ] **Step 1: Write the failing auth store and route behavior test**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/auth', () => ({
  login: vi.fn(async () => ({
    success: true,
    data: {
      user: { id: 1, employee_no: 'U1001', real_name: '张三', department: '研发', role_code: 'user', status: 'enabled' },
      menus: [
        { path: '/optimization-tasks', label: 'SQL优化建议' },
        { path: '/slow-sqls', label: '慢SQL列表' }
      ]
    }
  })),
  getCurrentUser: vi.fn(async () => ({ success: false }))
}))

import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('stores user info and home path after login', async () => {
    const store = useAuthStore()
    await store.login({
      employee_no: 'U1001',
      password: 'Passw0rd!'
    })
    expect(store.isAuthenticated).toBe(true)
    expect(store.roleCode).toBe('user')
    expect(store.homePath).toBe('/optimization-tasks')
  })
})
```

- [ ] **Step 2: Run the auth store test to verify it fails**

Run:

```bash
cd frontend && npm run test -- --run src/stores/auth.spec.ts
```

Expected: FAIL with `Cannot find module './auth'` or missing `useAuthStore`.

- [ ] **Step 3: Implement auth API, store, login page, router guard, shared pinia instance, and sidebar filtering**

`frontend/src/stores/index.ts`

```ts
import { createPinia } from 'pinia'

export const pinia = createPinia()
```

`frontend/src/main.ts`

```ts
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'

const app = createApp(App)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

`frontend/src/api/auth.ts`

```ts
import request from './request'
import type { ApiResponse, AuthPayload, LoginPayload } from '@/types'

export const login = (data: LoginPayload) =>
  request.post<AuthPayload, ApiResponse<AuthPayload>>('/auth/login', data)

export const logout = () =>
  request.post<{ logged_out: boolean }, ApiResponse<{ logged_out: boolean }>>('/auth/logout')

export const getCurrentUser = () =>
  request.get<AuthPayload, ApiResponse<AuthPayload>>('/auth/me')

export const getAuthorizedConnections = () =>
  request.get<{ items: any[] }, ApiResponse<{ items: any[] }>>('/auth/connections')
```

`frontend/src/stores/auth.ts`

```ts
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getCurrentUser, login as loginApi, logout as logoutApi } from '@/api/auth'
import type { AuthMenuItem, AuthUser } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const menus = ref<AuthMenuItem[]>([])
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const roleCode = computed(() => user.value?.role_code || 'user')
  const homePath = computed(() => '/optimization-tasks')

  async function login(payload: { employee_no: string; password: string }) {
    const res = await loginApi(payload)
    user.value = res.data.user
    menus.value = res.data.menus
    initialized.value = true
  }

  async function restore() {
    try {
      const res = await getCurrentUser()
      user.value = res.data.user
      menus.value = res.data.menus
    } catch {
      user.value = null
      menus.value = []
    } finally {
      initialized.value = true
    }
  }

  async function logout() {
    await logoutApi()
    user.value = null
    menus.value = []
  }

  function clear() {
    user.value = null
    menus.value = []
    initialized.value = true
  }

  return { user, menus, initialized, isAuthenticated, roleCode, homePath, login, restore, logout, clear }
})
```

`frontend/src/views/LoginView.vue`

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({
  employee_no: '',
  password: ''
})

async function handleSubmit() {
  loading.value = true
  try {
    await authStore.login(form)
    router.replace(authStore.homePath)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <h2>数据库运维平台登录</h2>
      <el-form @submit.prevent="handleSubmit">
        <el-form-item label="工号">
          <el-input v-model="form.employee_no" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSubmit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>
```

`frontend/src/router/index.ts`

```ts
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'
import { canAccessPath } from '@/auth/access'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/', redirect: '/optimization-tasks' },
  { path: '/optimization-tasks', component: () => import('@/views/OptimizationTaskList.vue') },
  { path: '/slow-sqls', component: () => import('@/views/SlowSQLList.vue') },
  { path: '/connections', component: () => import('@/views/ConnectionList.vue') },
  { path: '/users', component: () => import('@/views/UserManagement.vue') },
  { path: '/roles', component: () => import('@/views/RoleManagement.vue') },
  { path: '/permissions', component: () => import('@/views/PermissionManagement.vue') }
]

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  if (!authStore.initialized) {
    await authStore.restore()
  }
  if (to.meta.public) {
    if (authStore.isAuthenticated) {
      return authStore.homePath
    }
    return true
  }
  if (!authStore.isAuthenticated) {
    return '/login'
  }
  if (!canAccessPath(authStore.roleCode, to.path)) {
    return authStore.homePath
  }
  return true
})
```

`frontend/src/api/request.ts`

```ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true
})

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response
    }
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore(pinia)
      authStore.clear()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

`frontend/src/types/index.ts`

```ts
export interface AuthUser {
  id: number
  employee_no: string
  real_name: string
  department: string
  role_code: 'admin' | 'user'
  status: 'enabled' | 'disabled'
}

export interface AuthMenuItem {
  path: string
  label: string
}

export interface AuthPayload {
  user: AuthUser
  menus: AuthMenuItem[]
}

export interface LoginPayload {
  employee_no: string
  password: string
}
```

`frontend/src/components/Layout/Sidebar.vue`

```ts
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const visibleMenus = computed(() => authStore.menus)
```

- [ ] **Step 4: Run the auth store test and build the frontend**

Run:

```bash
cd frontend && npm run test -- --run src/stores/auth.spec.ts && npm run build
```

Expected: PASS for the auth store test and PASS for the Vite production build.

- [ ] **Step 5: Commit the frontend auth infrastructure task**

```bash
git add frontend/src/stores/index.ts frontend/src/api/auth.ts frontend/src/stores/auth.ts frontend/src/views/LoginView.vue frontend/src/main.ts frontend/src/router/index.ts frontend/src/api/request.ts frontend/src/components/Layout/Sidebar.vue frontend/src/types/index.ts frontend/src/stores/auth.spec.ts
git commit -m "feat: add frontend login flow and route guards"
```

## Task 8: Add Admin User Management, Role Management, And Permission Management Pages

**Files:**
- Create: `frontend/src/api/userAdmin.ts`
- Create: `frontend/src/api/permissionAdmin.ts`
- Create: `frontend/src/stores/userAdmin.ts`
- Create: `frontend/src/stores/permissionAdmin.ts`
- Create: `frontend/src/views/UserManagement.vue`
- Create: `frontend/src/views/RoleManagement.vue`
- Create: `frontend/src/views/PermissionManagement.vue`
- Test: `frontend/src/stores/userAdmin.spec.ts`

- [ ] **Step 1: Write the failing admin store test**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/userAdmin', () => ({
  getUserList: vi.fn(async () => ({
    success: true,
    data: {
      items: [
        { id: 1, employee_no: 'U1001', real_name: '张三', department: '研发', role_code: 'user', status: 'enabled' }
      ]
    }
  }))
}))

import { useUserAdminStore } from './userAdmin'

describe('user admin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads user list', async () => {
    const store = useUserAdminStore()
    await store.fetchList()
    expect(store.list).toHaveLength(1)
    expect(store.list[0].employee_no).toBe('U1001')
  })
})
```

- [ ] **Step 2: Run the admin store test to verify it fails**

Run:

```bash
cd frontend && npm run test -- --run src/stores/userAdmin.spec.ts
```

Expected: FAIL with `Cannot find module './userAdmin'`.

- [ ] **Step 3: Implement admin APIs, stores, and three management pages**

`frontend/src/api/userAdmin.ts`

```ts
import request from './request'

export const getUserList = () => request.get('/admin/users')
export const createUser = (data: any) => request.post('/admin/users', data)
export const updateUser = (id: number, data: any) => request.put(`/admin/users/${id}`, data)
export const updateUserStatus = (id: number, status: string) =>
  request.put(`/admin/users/${id}/status`, { status })
export const resetUserPassword = (id: number, password: string) =>
  request.put(`/admin/users/${id}/reset-password`, { password })
export const deleteUser = (id: number) => request.delete(`/admin/users/${id}`)
```

`frontend/src/api/permissionAdmin.ts`

```ts
import request from './request'

export const getRoles = () => request.get('/admin/roles')
export const getUserConnectionPermissions = (userId: number) =>
  request.get(`/admin/user-connection-permissions/${userId}`)
export const saveUserConnectionPermissions = (userId: number, connectionIds: number[]) =>
  request.put(`/admin/user-connection-permissions/${userId}`, { connection_ids: connectionIds })
```

`frontend/src/stores/userAdmin.ts`

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createUser, deleteUser, getUserList, resetUserPassword, updateUser, updateUserStatus } from '@/api/userAdmin'

export const useUserAdminStore = defineStore('userAdmin', () => {
  const list = ref<any[]>([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res = await getUserList()
      list.value = res.data.items
    } finally {
      loading.value = false
    }
  }

  async function addUser(payload: any) {
    await createUser(payload)
    await fetchList()
  }

  async function editUser(id: number, payload: any) {
    await updateUser(id, payload)
    await fetchList()
  }

  async function setUserStatus(id: number, status: string) {
    await updateUserStatus(id, status)
    await fetchList()
  }

  async function resetPassword(id: number, password: string) {
    await resetUserPassword(id, password)
  }

  async function removeUser(id: number) {
    await deleteUser(id)
    await fetchList()
  }

  return { list, loading, fetchList, addUser, editUser, setUserStatus, resetPassword, removeUser }
})
```

`frontend/src/stores/permissionAdmin.ts`

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getRoles, getUserConnectionPermissions, saveUserConnectionPermissions } from '@/api/permissionAdmin'
import { getConnectionList } from '@/api/dbConnection'

export const usePermissionAdminStore = defineStore('permissionAdmin', () => {
  const roles = ref<any[]>([])
  const connections = ref<any[]>([])
  const selectedConnectionIds = ref<number[]>([])

  async function fetchRoles() {
    const res = await getRoles()
    roles.value = res.data
  }

  async function fetchConnections() {
    const res = await getConnectionList({ page: 1, per_page: 1000 })
    connections.value = res.data.items
  }

  async function loadUserPermissions(userId: number) {
    const res = await getUserConnectionPermissions(userId)
    selectedConnectionIds.value = res.data.connection_ids
  }

  async function saveUserPermissions(userId: number) {
    await saveUserConnectionPermissions(userId, selectedConnectionIds.value)
  }

  return { roles, connections, selectedConnectionIds, fetchRoles, fetchConnections, loadUserPermissions, saveUserPermissions }
})
```

`frontend/src/views/UserManagement.vue`

```vue
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useUserAdminStore } from '@/stores/userAdmin'

const store = useUserAdminStore()
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  employee_no: '',
  password: 'InitPass123',
  real_name: '',
  department: '',
  role_code: 'user',
  status: 'enabled'
})

onMounted(() => {
  store.fetchList()
})

function openCreateDialog() {
  editingId.value = null
  Object.assign(form, {
    employee_no: '',
    password: 'InitPass123',
    real_name: '',
    department: '',
    role_code: 'user',
    status: 'enabled'
  })
  dialogVisible.value = true
}

function openEditDialog(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    employee_no: row.employee_no,
    password: 'InitPass123',
    real_name: row.real_name,
    department: row.department,
    role_code: row.role_code,
    status: row.status
  })
  dialogVisible.value = true
}

async function submitForm() {
  if (editingId.value) {
    await store.editUser(editingId.value, {
      real_name: form.real_name,
      department: form.department,
      role_code: form.role_code,
      status: form.status
    })
  } else {
    await store.addUser({ ...form })
  }
  dialogVisible.value = false
}

function toggleStatus(row: any) {
  store.setUserStatus(row.id, row.status === 'enabled' ? 'disabled' : 'enabled')
}

function openResetPasswordDialog(row: any) {
  store.resetPassword(row.id, 'InitPass123')
}

function removeRow(row: any) {
  store.removeUser(row.id)
}
</script>

<template>
  <AppLayout>
    <div class="page-header"><h2>用户管理</h2></div>
    <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
    <el-table :data="store.list" v-loading="store.loading" style="margin-top: 16px">
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="employee_no" label="工号" />
      <el-table-column prop="department" label="部门" />
      <el-table-column prop="role_code" label="角色" />
      <el-table-column prop="status" label="状态" />
      <el-table-column label="操作" width="320">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="warning" @click="toggleStatus(row)">
            {{ row.status === 'enabled' ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="info" @click="openResetPasswordDialog(row)">重置密码</el-button>
          <el-button link type="danger" @click="removeRow(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'">
      <el-form>
        <el-form-item label="工号">
          <el-input v-model="form.employee_no" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="初始密码">
          <el-input v-model="form.password" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_code">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
```

`frontend/src/views/RoleManagement.vue`

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'

const permissionStore = usePermissionAdminStore()

onMounted(() => {
  permissionStore.fetchRoles()
})
</script>

<template>
  <AppLayout>
    <div class="page-header"><h2>角色管理</h2></div>
    <el-card v-for="role in permissionStore.roles" :key="role.code" shadow="never">
      <h3>{{ role.name }}</h3>
      <p>{{ role.data_scope }}</p>
    </el-card>
  </AppLayout>
</template>
```

`frontend/src/views/PermissionManagement.vue`

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'
import { useUserAdminStore } from '@/stores/userAdmin'

const permissionStore = usePermissionAdminStore()
const userStore = useUserAdminStore()
const currentUserId = ref<number | null>(null)

onMounted(async () => {
  await userStore.fetchList()
  await permissionStore.fetchConnections()
})

async function selectUser(row: any) {
  currentUserId.value = row.id
  await permissionStore.loadUserPermissions(row.id)
}

async function savePermissions() {
  if (currentUserId.value) {
    await permissionStore.saveUserPermissions(currentUserId.value)
  }
}
</script>

<template>
  <AppLayout>
    <div class="page-header"><h2>权限管理</h2></div>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-table :data="userStore.list" @row-click="selectUser">
          <el-table-column prop="real_name" label="姓名" />
          <el-table-column prop="employee_no" label="工号" />
        </el-table>
      </el-col>
      <el-col :span="16">
        <el-checkbox-group v-model="permissionStore.selectedConnectionIds">
          <el-checkbox v-for="connection in permissionStore.connections" :key="connection.id" :value="connection.id">
            {{ connection.connection_name }} / {{ connection.manage_host }}
          </el-checkbox>
        </el-checkbox-group>
        <el-button type="primary" style="margin-top: 16px" @click="savePermissions">保存授权</el-button>
      </el-col>
    </el-row>
  </AppLayout>
</template>
```

- [ ] **Step 4: Run the admin store test and build the frontend**

Run:

```bash
cd frontend && npm run test -- --run src/stores/userAdmin.spec.ts && npm run build
```

Expected: PASS for the admin store test and PASS for the build.

- [ ] **Step 5: Commit the admin pages task**

```bash
git add frontend/src/api/userAdmin.ts frontend/src/api/permissionAdmin.ts frontend/src/stores/userAdmin.ts frontend/src/stores/permissionAdmin.ts frontend/src/views/UserManagement.vue frontend/src/views/RoleManagement.vue frontend/src/views/PermissionManagement.vue frontend/src/stores/userAdmin.spec.ts
git commit -m "feat: add admin user role and permission pages"
```

## Task 9: Restrict Optimization Task Creation UI To Authorized Connections

**Files:**
- Modify: `frontend/src/views/OptimizationTaskCreateSql.vue`
- Modify: `frontend/src/views/OptimizationTaskCreateMyBatis.vue`
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/types/index.ts`
- Test: `frontend/src/stores/auth.spec.ts`

- [ ] **Step 1: Extend the existing auth store test with authorized connections**

```ts
vi.mock('@/api/auth', () => ({
  login: vi.fn(async () => ({
    success: true,
    data: {
      user: { id: 1, employee_no: 'U1001', real_name: '张三', department: '研发', role_code: 'user', status: 'enabled' },
      menus: [
        { path: '/optimization-tasks', label: 'SQL优化建议' },
        { path: '/slow-sqls', label: '慢SQL列表' }
      ]
    }
  })),
  getCurrentUser: vi.fn(async () => ({ success: false })),
  getAuthorizedConnections: vi.fn(async () => ({
    success: true,
    data: {
      items: [
        { id: 10, connection_name: '业务库', host: '10.0.0.10', manage_host: '10.0.0.11', port: 3306, username: 'root', is_enabled: true }
      ]
    }
  }))
}))

it('loads authorized connections for dropdown usage', async () => {
  const store = useAuthStore()
  await store.fetchAuthorizedConnections()
  expect(store.authorizedConnections).toHaveLength(1)
  expect(store.authorizedConnections[0].connection_name).toBe('业务库')
})
```

- [ ] **Step 2: Run the auth store test to verify it fails**

Run:

```bash
cd frontend && npm run test -- --run src/stores/auth.spec.ts
```

Expected: FAIL because `fetchAuthorizedConnections` and `authorizedConnections` do not exist.

- [ ] **Step 3: Load authorized connections into auth store and consume them in both optimization create pages**

`frontend/src/stores/auth.ts`

```ts
import { getAuthorizedConnections } from '@/api/auth'

const authorizedConnections = ref<any[]>([])

async function fetchAuthorizedConnections() {
  const res = await getAuthorizedConnections()
  authorizedConnections.value = res.data.items
}

return {
  user,
  menus,
  initialized,
  isAuthenticated,
  roleCode,
  homePath,
  authorizedConnections,
  login,
  restore,
  logout,
  clear,
  fetchAuthorizedConnections
}
```

`frontend/src/views/OptimizationTaskCreateSql.vue`

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }
})
</script>

<template>
  <AppLayout>
    <el-form>
      <el-form-item label="数据库连接">
        <el-select v-model="form.db_connection_id" placeholder="请选择数据库连接">
          <el-option
            v-for="connection in authStore.authorizedConnections"
            :key="connection.id"
            :label="`${connection.connection_name} / ${connection.host}`"
            :value="connection.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
  </AppLayout>
</template>
```

`frontend/src/views/OptimizationTaskCreateMyBatis.vue`

```vue
<el-form-item label="数据库连接">
  <el-select v-model="form.db_connection_id" placeholder="请选择数据库连接">
    <el-option
      v-for="connection in authStore.authorizedConnections"
      :key="connection.id"
      :label="`${connection.connection_name} / ${connection.host}`"
      :value="connection.id"
    />
  </el-select>
</el-form-item>
```

- [ ] **Step 4: Run the auth store test and production build**

Run:

```bash
cd frontend && npm run test -- --run src/stores/auth.spec.ts && npm run build
```

Expected: PASS for the extended auth store test and PASS for the build.

- [ ] **Step 5: Commit the optimization create page authorization task**

```bash
git add frontend/src/stores/auth.ts frontend/src/views/OptimizationTaskCreateSql.vue frontend/src/views/OptimizationTaskCreateMyBatis.vue frontend/src/stores/auth.spec.ts frontend/src/types/index.ts
git commit -m "feat: limit optimization task forms to authorized connections"
```

## Task 10: Run Full Verification And Capture Manual QA

**Files:**
- Modify: `docs/superpowers/specs/2026-04-02-auth-role-permission-design.md`

- [ ] **Step 1: Run the full backend test suite for auth and permission features**

Run:

```bash
cd backend && ../venv/bin/python -m unittest \
  tests.test_schema_migration_service \
  tests.test_auth_api \
  tests.test_admin_user_api \
  tests.test_optimization_task_permissions \
  tests.test_slow_sql_query_service \
  tests.test_optimization_task_service -v
```

Expected: PASS for all six test modules.

- [ ] **Step 2: Run the frontend unit tests and production build**

Run:

```bash
cd frontend && npm run test -- --run src/auth/access.spec.ts src/stores/auth.spec.ts src/stores/userAdmin.spec.ts && npm run build
```

Expected: PASS for all Vitest suites and PASS for the build.

- [ ] **Step 3: Execute the manual QA checklist in a browser**

```text
1. 以管理员账号登录，确认左侧菜单包含 SQL优化建议、慢SQL列表、连接管理、归档任务、执行日志、用户管理、角色管理、权限管理。
2. 在用户管理中新增一个普通用户 U2001，并设置初始密码。
3. 在权限管理中给 U2001 分配 1 个连接。
4. 退出管理员，使用 U2001 登录，确认左侧菜单只剩 SQL优化建议、慢SQL列表。
5. 进入 SQL优化建议 创建页，确认连接下拉中只有已授权连接。
6. 创建 1 条 SQL 优化任务，确认任务列表中可见。
7. 再创建另一个普通用户 U2002，用管理员给 U2002 分配同一连接。
8. 用 U2002 登录，确认 SQL优化建议 列表中看不到 U2001 创建的任务。
9. 用 U2002 登录进入 慢SQL列表，确认可看到该连接对应的慢 SQL 数据。
10. 用管理员禁用 U2001，刷新 U2001 浏览器页面，确认接口返回 401 并跳回登录页。
```

- [ ] **Step 4: Record verification notes in the design spec**

```markdown
## 实施后人工验证记录

- 管理员菜单验证：通过
- 普通用户菜单验证：通过
- 连接授权限制验证：通过
- SQL优化建议按创建人过滤验证：通过
- 慢SQL按 manage_host 过滤验证：通过
- 禁用用户即时失效验证：通过
```

- [ ] **Step 5: Commit the verification results**

```bash
git add docs/superpowers/specs/2026-04-02-auth-role-permission-design.md
git commit -m "docs: record auth and permission verification results"
```
