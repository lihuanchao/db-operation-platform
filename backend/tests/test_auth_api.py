import os
import unittest

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret'

from app import app
from extensions import db
from models.sys_user import SysUser
from services.auth_service import AuthService


class AuthApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='test-secret')
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
