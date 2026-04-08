import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'execution-log-secret'

from app import app
from extensions import db
from models.archive_task import ArchiveTask
from models.db_connection import DbConnection
from models.execution_log import ExecutionLog
from models.flashback_task import FlashbackTask
from models.sys_user import SysUser
from services.auth_service import AuthService
from services.flashback_service import FlashbackService


class ExecutionLogApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='execution-log-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        self.temp_dir = tempfile.mkdtemp(prefix='execution-log-api-')
        self.original_output_root = FlashbackService.OUTPUT_ROOT
        FlashbackService.OUTPUT_ROOT = self.temp_dir
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
        self.connection = DbConnection(
            id=1,
            connection_name='测试连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1,
        )
        db.session.add_all([self.admin, self.connection])
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
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.ctx.pop()

    def _create_archive_log(self):
        archive_task = ArchiveTask(
            id=1,
            task_name='归档任务',
            source_connection_id=self.connection.id,
            source_database='demo_db',
            source_table='orders',
            is_enabled=1,
        )
        db.session.add(archive_task)
        db.session.commit()

        log = ExecutionLog(
            id=1,
            task_id=archive_task.id,
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now() - timedelta(minutes=1),
            status=1,
            log_file=os.path.join(self.temp_dir, 'archive.log'),
            error_message=None,
        )
        db.session.add(log)
        db.session.commit()
        return log

    def _create_flashback_task(self, status='completed'):
        task = FlashbackTask(
            db_connection_id=self.connection.id,
            connection_id=self.connection.id,
            connection_name=self.connection.connection_name,
            database_name='demo_db',
            table_name='orders',
            mode='repl',
            sql_type='delete',
            work_type='2sql',
            status=status,
            progress=100 if status == 'completed' else 30,
            log_file=os.path.join(self.temp_dir, 'flashback', 'run.log'),
            error_message=None,
            created_at=datetime.now() - timedelta(minutes=2),
            updated_at=datetime.now() - timedelta(minutes=1),
            started_at=datetime.now() - timedelta(minutes=2),
            finished_at=datetime.now() - timedelta(minutes=1),
        )
        db.session.add(task)
        db.session.commit()

        os.makedirs(os.path.dirname(task.log_file), exist_ok=True)
        with open(task.log_file, 'w', encoding='utf-8') as file_obj:
            file_obj.write('flashback log content')
        return task

    def test_get_execution_logs_filters_flashback_logs_and_normalizes_structure(self):
        self._create_archive_log()
        task = self._create_flashback_task(status='completed')

        response = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=flashback')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        data = body['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(len(data['items']), 1)

        item = data['items'][0]
        self.assertEqual(item['id'], task.id)
        self.assertEqual(item['log_type'], 'flashback')
        self.assertEqual(item['status'], 1)
        self.assertEqual(item['detail_path'], f'/flashback-tasks/{task.id}')
        self.assertIn('task_name', item)

    def test_get_flashback_log_content_returns_log_file_content(self):
        task = self._create_flashback_task(status='running')

        response = self.client.get(f'/api/execution-logs/flashback/{task.id}/log-content')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['content'], 'flashback log content')
        self.assertTrue(body['data']['has_file'])


if __name__ == '__main__':
    unittest.main()
