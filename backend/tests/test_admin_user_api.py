import os
import unittest

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'admin-secret'

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.sys_user import SysUser
from services.auth_service import AuthService


class AdminUserApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='admin-secret')
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
            id=1,
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
