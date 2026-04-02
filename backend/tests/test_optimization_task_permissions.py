import os
import unittest

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'opt-secret'

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.optimization_task import OptimizationTask
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission
from services.auth_service import AuthService


class OptimizationTaskPermissionTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='opt-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        self.admin = SysUser(
            employee_no='A1',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled'
        )
        self.user = SysUser(
            employee_no='U1',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='普通用户',
            department='研发',
            role_code='user',
            status='enabled'
        )
        self.other = SysUser(
            employee_no='U2',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='其他用户',
            department='研发',
            role_code='user',
            status='enabled'
        )
        self.connection = DbConnection(
            id=1,
            connection_name='授权连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1
        )
        db.session.add_all([self.admin, self.user, self.other, self.connection])
        db.session.commit()
        db.session.add(UserConnectionPermission(user_id=self.user.id, connection_id=self.connection.id, status='enabled'))
        db.session.add(OptimizationTask(
            id=1,
            task_type='sql',
            object_content='select 1',
            object_preview='select 1',
            db_connection_id=self.connection.id,
            database_name='demo',
            database_host='10.0.0.10',
            connection_id=self.connection.id,
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
        self.client.post('/api/auth/login', json={'employee_no': 'U1', 'password': 'Passw0rd!'})
        response = self.client.get('/api/optimization-tasks/1')
        self.assertEqual(response.status_code, 404)

    def test_normal_user_cannot_create_task_for_unauthorized_connection(self):
        unauthorized = DbConnection(
            id=2,
            connection_name='未授权连接',
            host='10.0.0.20',
            manage_host='10.0.0.21',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1
        )
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
