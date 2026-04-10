import os
import unittest
import shutil
import tempfile
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
        self.output_root = tempfile.mkdtemp(prefix='flashback-task-root-')
        self.original_output_root = FlashbackService.OUTPUT_ROOT
        FlashbackService.OUTPUT_ROOT = self.output_root
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
        FlashbackService.OUTPUT_ROOT = self.original_output_root
        shutil.rmtree(self.output_root, ignore_errors=True)
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

    def _prepare_output_tree(self, task, with_artifacts=True):
        task_dir = os.path.join(self.output_root, str(task.id))
        output_dir = os.path.join(task_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        if with_artifacts:
            for name in ['binlog_status.txt', 'biglong_trx.txt', 'a.sql']:
                with open(os.path.join(output_dir, name), 'w', encoding='utf-8') as file_obj:
                    file_obj.write(name)
        return output_dir

    def test_create_flashback_task_queues_task_and_starts_async_runner(self):
        payload = {
            'db_connection_id': self.enabled_connection.id,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
        }

        with patch.object(FlashbackService, '_run_task_async', create=True) as mock_run_task_async:
            mock_run_task_async.return_value = (True, None)
            response = self.client.post('/api/flashback-tasks', json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        task = body['data']
        self.assertEqual(task['status'], 'queued')
        self.assertEqual(task['mode'], 'repl')
        self.assertEqual(task['progress'], 0)
        self.assertEqual(task['connection_name'], self.enabled_connection.connection_name)
        self.assertEqual(task['db_connection_id'], self.enabled_connection.id)
        self.assertEqual(task['database_name'], 'demo_db')
        self.assertEqual(task['table_name'], 'orders')
        self.assertEqual(task['creator_user_id'], self.admin.id)
        self.assertEqual(task['creator_employee_no'], self.admin.employee_no)
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

    def test_create_flashback_task_rejects_non_integer_connection_id(self):
        payload = {
            'db_connection_id': 'abc',
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
        }

        response = self.client.post('/api/flashback-tasks', json=payload)

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body['success'])
        self.assertEqual(body['error'], 'db_connection_id 必须为整数')
        self.assertNotIn('ValueError', body['error'])
        self.assertNotIn('invalid literal', body['error'])

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

    def test_list_flashback_tasks_clamps_zero_per_page(self):
        self._create_task()

        response = self.client.get('/api/flashback-tasks?page=1&per_page=0')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertEqual(data['pagination']['per_page'], 1)
        self.assertEqual(data['pagination']['total_pages'], 1)

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

    def test_execute_task_marks_completed_and_collects_artifacts(self):
        task = self._create_task()
        output_dir = self._prepare_output_tree(task, with_artifacts=True)

        class FakeProcess:
            def wait(self):
                return 0

        with patch.object(FlashbackService, 'build_command', return_value=(['/bin/echo', 'ok'], '/bin/echo ok')):
            with patch('services.flashback_service.subprocess.Popen', return_value=FakeProcess()):
                FlashbackService._execute_task(task.id)

        refreshed = db.session.get(FlashbackTask, task.id)
        self.assertEqual(refreshed.status, 'completed')
        self.assertEqual(refreshed.progress, 100)
        self.assertIsNotNone(refreshed.started_at)
        self.assertIsNotNone(refreshed.finished_at)
        self.assertEqual(refreshed.output_dir, output_dir)
        self.assertTrue(refreshed.log_file.endswith('run.log'))
        self.assertEqual([item['id'] for item in refreshed.get_artifacts()], ['binlog-status', 'biglong-trx', 'result-sql'])

    def test_execute_task_marks_failed_on_nonzero_exit(self):
        task = self._create_task()
        self._prepare_output_tree(task, with_artifacts=False)

        class FakeProcess:
            def wait(self):
                return 7

        with patch.object(FlashbackService, 'build_command', return_value=(['/bin/echo', 'ok'], '/bin/echo ok')):
            with patch('services.flashback_service.subprocess.Popen', return_value=FakeProcess()):
                FlashbackService._execute_task(task.id)

        refreshed = db.session.get(FlashbackTask, task.id)
        self.assertEqual(refreshed.status, 'failed')
        self.assertEqual(refreshed.progress, 100)
        self.assertIsNotNone(refreshed.finished_at)
        self.assertIn('7', refreshed.error_message)

    def test_execute_task_marks_failed_when_build_command_raises(self):
        task = self._create_task()
        self._prepare_output_tree(task, with_artifacts=False)

        with patch.object(FlashbackService, 'build_command', side_effect=RuntimeError('build failed')):
            FlashbackService._execute_task(task.id)

        refreshed = db.session.get(FlashbackTask, task.id)
        self.assertEqual(refreshed.status, 'failed')
        self.assertEqual(refreshed.progress, 100)
        self.assertIsNotNone(refreshed.finished_at)
        self.assertIn('build failed', refreshed.error_message)

    def test_execute_task_marks_failed_when_collect_artifacts_raises(self):
        task = self._create_task()
        self._prepare_output_tree(task, with_artifacts=False)

        class FakeProcess:
            def wait(self):
                return 0

        with patch.object(FlashbackService, 'build_command', return_value=(['/bin/echo', 'ok'], '/bin/echo ok')):
            with patch('services.flashback_service.subprocess.Popen', return_value=FakeProcess()):
                with patch.object(FlashbackService, 'collect_artifacts', side_effect=FileNotFoundError('missing')):
                    FlashbackService._execute_task(task.id)

        refreshed = db.session.get(FlashbackTask, task.id)
        self.assertEqual(refreshed.status, 'failed')
        self.assertEqual(refreshed.progress, 100)
        self.assertIsNotNone(refreshed.finished_at)
        self.assertIn('missing', refreshed.error_message)

    def test_create_flashback_task_marks_failed_when_worker_start_fails(self):
        payload = {
            'db_connection_id': self.enabled_connection.id,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
        }

        with patch('services.flashback_service.threading.Thread.start', side_effect=RuntimeError('start failed')):
            response = self.client.post('/api/flashback-tasks', json=payload)

        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body['success'])
        self.assertIn('start failed', body['error'])

        persisted_task = FlashbackTask.query.order_by(FlashbackTask.id.desc()).first()
        self.assertEqual(persisted_task.status, 'failed')
        self.assertEqual(persisted_task.progress, 100)
        self.assertIsNotNone(persisted_task.finished_at)
        self.assertIn('start failed', persisted_task.error_message)

    def test_run_task_async_does_not_depend_on_importing_app_module(self):
        task = self._create_task()
        original_import = __import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'app':
                raise ModuleNotFoundError("No module named 'app'")
            return original_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=guarded_import):
            with patch('services.flashback_service.threading.Thread.start', return_value=None) as mock_start:
                started, error = FlashbackService._run_task_async(task.id)

        self.assertTrue(started)
        self.assertIsNone(error)
        self.assertEqual(mock_start.call_count, 1)


if __name__ == '__main__':
    unittest.main()
