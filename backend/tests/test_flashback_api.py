import os
import unittest
from unittest.mock import patch

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'flashback-secret'

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.flashback_task import FlashbackTask
from models.sys_user import SysUser
from services.auth_service import AuthService
from services.flashback_service import FlashbackService


class FlashbackApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='flashback-secret')
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
            status='enabled',
        )
        self.enabled_connection = DbConnection(
            id=1,
            connection_name='启用连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1,
        )
        self.disabled_connection = DbConnection(
            id=2,
            connection_name='禁用连接',
            host='10.0.0.20',
            manage_host='10.0.0.21',
            port=3306,
            username='root',
            password='secret',
            is_enabled=0,
        )
        db.session.add_all([self.admin, self.enabled_connection, self.disabled_connection])
        db.session.commit()

        login_response = self.client.post('/api/auth/login', json={
            'employee_no': 'A1001',
            'password': 'Passw0rd!',
        })
        self.assertEqual(login_response.status_code, 200)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _create_task(self, **overrides):
        data = {
            'db_connection_id': self.enabled_connection.id,
            'connection_id': self.enabled_connection.id,
            'connection_name': self.enabled_connection.connection_name,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'mode': 'repl',
            'sql_type': 'delete',
            'work_type': '2sql',
            'status': 'queued',
            'progress': 0,
        }
        data.update(overrides)
        task = FlashbackTask(**data)
        db.session.add(task)
        db.session.commit()
        return task

    def test_create_flashback_task_queues_task_and_starts_async_runner(self):
        payload = {
            'db_connection_id': self.enabled_connection.id,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
        }

        with patch.object(FlashbackService, '_run_task_async', create=True) as mock_run_task_async:
            response = self.client.post('/api/flashback-tasks', json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        task = body['data']
        self.assertEqual(task['status'], 'queued')
        self.assertEqual(task['connection_name'], self.enabled_connection.connection_name)
        self.assertEqual(task['db_connection_id'], self.enabled_connection.id)
        self.assertEqual(task['database_name'], 'demo_db')
        self.assertEqual(task['table_name'], 'orders')
        self.assertEqual(mock_run_task_async.call_count, 1)

    def test_create_flashback_task_rejects_disabled_connection(self):
        payload = {
            'db_connection_id': self.disabled_connection.id,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
        }

        with patch.object(FlashbackService, '_run_task_async', create=True) as mock_run_task_async:
            response = self.client.post('/api/flashback-tasks', json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()['success'])
        self.assertIn('连接', response.get_json()['error'])
        self.assertEqual(mock_run_task_async.call_count, 0)

    def test_list_flashback_tasks_supports_pagination(self):
        first_task = self._create_task()
        second_task = self._create_task(database_name='audit_db', table_name='events', sql_type='insert')

        response = self.client.get('/api/flashback-tasks?page=1&per_page=1')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        data = body['data']
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['per_page'], 1)
        self.assertEqual(data['pagination']['total'], 2)
        self.assertEqual(len(data['items']), 1)
        self.assertIn(data['items'][0]['id'], {first_task.id, second_task.id})

    def test_get_flashback_task_detail_returns_task(self):
        task = self._create_task(status='running', progress=30)

        response = self.client.get(f'/api/flashback-tasks/{task.id}')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        data = body['data']
        self.assertEqual(data['id'], task.id)
        self.assertEqual(data['connection_name'], self.enabled_connection.connection_name)
        self.assertEqual(data['status'], 'running')
        self.assertEqual(data['progress'], 30)


if __name__ == '__main__':
    unittest.main()
