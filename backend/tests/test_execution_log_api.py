import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

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
        self.escape_dir = tempfile.mkdtemp(prefix='execution-log-escape-')
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
        shutil.rmtree(self.escape_dir, ignore_errors=True)
        self.ctx.pop()

    def _create_archive_log(self, task_id=1, log_id=1, start_time=None, end_time=None, status=1):
        archive_task = ArchiveTask(
            id=task_id,
            task_name=f'归档任务-{task_id}',
            source_connection_id=self.connection.id,
            source_database='demo_db',
            source_table='orders',
            is_enabled=1,
        )
        db.session.add(archive_task)
        db.session.commit()

        start_time = start_time or (datetime.now() - timedelta(minutes=5))
        end_time = end_time or (datetime.now() - timedelta(minutes=1))
        log = ExecutionLog(
            id=log_id,
            task_id=archive_task.id,
            start_time=start_time,
            end_time=end_time,
            status=status,
            log_file=os.path.join(self.temp_dir, f'archive-{log_id}.log'),
            error_message=None,
        )
        db.session.add(log)
        db.session.commit()
        return log

    def _create_flashback_task(
        self,
        task_id=2,
        status='completed',
        started_at=None,
        finished_at=None,
        log_file_path=None,
        log_content='flashback log content',
        artifacts=None,
    ):
        task = FlashbackTask(
            id=task_id,
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
            error_message=None,
            created_at=datetime.now() - timedelta(minutes=2),
            updated_at=datetime.now() - timedelta(minutes=1),
            started_at=started_at or (datetime.now() - timedelta(minutes=2)),
            finished_at=finished_at or (datetime.now() - timedelta(minutes=1)),
        )
        db.session.add(task)
        db.session.commit()

        task_root = os.path.join(self.temp_dir, str(task.id))
        os.makedirs(task_root, exist_ok=True)
        log_file_path = log_file_path or os.path.join(task_root, 'run.log')
        if log_content is not None:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            with open(log_file_path, 'w', encoding='utf-8') as file_obj:
                file_obj.write(log_content)
        task.log_file = log_file_path

        if artifacts is not None:
            normalized_artifacts = []
            task_root = os.path.join(self.temp_dir, str(task.id))
            for artifact in artifacts:
                artifact_path = artifact['path']
                absolute_path = artifact_path if os.path.isabs(artifact_path) else os.path.join(task_root, artifact_path)
                os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                content = artifact.get('content', '')
                if content is not None:
                    with open(absolute_path, 'w', encoding='utf-8') as file_obj:
                        file_obj.write(content)
                normalized_artifacts.append({
                    'id': artifact['id'],
                    'name': artifact.get('name') or os.path.basename(absolute_path),
                    'path': artifact_path,
                    'size': os.path.getsize(absolute_path),
                })
            task.set_artifacts(normalized_artifacts)

        db.session.commit()
        return task

    def test_default_execution_logs_stays_archive_only(self):
        self._create_archive_log()
        self._create_flashback_task()

        response = self.client.get('/api/execution-logs?page=1&per_page=10')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        data = body['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['log_type'], 'archive')

    def test_execution_logs_support_flashback_and_all_views(self):
        event_time = datetime(2026, 4, 8, 10, 0, 0)
        archive_log = self._create_archive_log(task_id=10, log_id=10, start_time=event_time, end_time=event_time)
        flashback_task = self._create_flashback_task(task_id=11, started_at=event_time, finished_at=event_time)

        flashback_response = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=flashback')
        self.assertEqual(flashback_response.status_code, 200)
        flashback_data = flashback_response.get_json()['data']
        self.assertEqual(flashback_data['total'], 1)
        self.assertEqual(len(flashback_data['items']), 1)
        self.assertEqual(flashback_data['items'][0]['id'], flashback_task.id)
        self.assertEqual(flashback_data['items'][0]['log_type'], 'flashback')

        all_response = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=all')
        self.assertEqual(all_response.status_code, 200)
        all_data = all_response.get_json()['data']
        self.assertEqual(all_data['total'], 2)
        self.assertEqual([item['id'] for item in all_data['items']], [flashback_task.id, archive_log.id])
        self.assertEqual([item['log_type'] for item in all_data['items']], ['flashback', 'archive'])

    def test_execution_logs_support_flashback_task_name_search_with_serialized_name(self):
        flashback_task = self._create_flashback_task(
            task_id=12,
            status='completed',
            started_at=datetime(2026, 4, 8, 10, 5, 0),
            finished_at=datetime(2026, 4, 8, 10, 6, 0),
        )

        flashback_response = self.client.get(
            '/api/execution-logs?page=1&per_page=10&log_type=flashback&task_name=demo_db.orders'
        )
        all_response = self.client.get(
            '/api/execution-logs?page=1&per_page=10&log_type=all&task_name=demo_db.orders'
        )

        self.assertEqual(flashback_response.status_code, 200)
        self.assertEqual(all_response.status_code, 200)
        self.assertEqual(flashback_response.get_json()['data']['total'], 1)
        self.assertEqual(flashback_response.get_json()['data']['items'][0]['id'], flashback_task.id)
        self.assertEqual(all_response.get_json()['data']['total'], 1)
        self.assertEqual(all_response.get_json()['data']['items'][0]['id'], flashback_task.id)

    def test_execution_logs_stable_order_across_pages_for_equal_timestamps(self):
        event_time = datetime(2026, 4, 8, 10, 0, 0)
        first_archive = self._create_archive_log(task_id=30, log_id=30, start_time=event_time, end_time=event_time)
        second_flashback = self._create_flashback_task(task_id=31, started_at=event_time, finished_at=event_time)
        third_archive = self._create_archive_log(task_id=32, log_id=32, start_time=event_time, end_time=event_time)

        page1 = self.client.get('/api/execution-logs?page=1&per_page=1&log_type=all')
        page2 = self.client.get('/api/execution-logs?page=2&per_page=1&log_type=all')
        page3 = self.client.get('/api/execution-logs?page=3&per_page=1&log_type=all')

        self.assertEqual(page1.status_code, 200)
        self.assertEqual(page2.status_code, 200)
        self.assertEqual(page3.status_code, 200)
        self.assertEqual(page1.get_json()['data']['items'][0]['id'], third_archive.id)
        self.assertEqual(page2.get_json()['data']['items'][0]['id'], second_flashback.id)
        self.assertEqual(page3.get_json()['data']['items'][0]['id'], first_archive.id)

    def test_flashback_status_filter_maps_queued_running_and_failed(self):
        queued_task = self._create_flashback_task(task_id=40, status='queued')
        running_task = self._create_flashback_task(task_id=41, status='running')
        failed_task = self._create_flashback_task(task_id=42, status='failed')

        queued_resp = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=flashback&status=2')
        failed_resp = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=flashback&status=0')

        self.assertEqual(queued_resp.status_code, 200)
        self.assertEqual(failed_resp.status_code, 200)
        self.assertEqual(queued_resp.get_json()['data']['total'], 2)
        self.assertCountEqual(
            [item['id'] for item in queued_resp.get_json()['data']['items']],
            [queued_task.id, running_task.id],
        )
        self.assertEqual(failed_resp.get_json()['data']['total'], 1)
        self.assertEqual(failed_resp.get_json()['data']['items'][0]['id'], failed_task.id)

    def test_flashback_log_content_rejects_log_file_outside_task_root(self):
        rogue_log = os.path.join(self.escape_dir, 'rogue.log')
        with open(rogue_log, 'w', encoding='utf-8') as file_obj:
            file_obj.write('rogue content')
        task = self._create_flashback_task(task_id=20, log_file_path=rogue_log, log_content=None)

        response = self.client.get(f'/api/execution-logs/flashback/{task.id}/log-content')

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()['success'])

    def test_flashback_typed_log_content_reads_file_and_surfaces_io_errors(self):
        task = self._create_flashback_task(task_id=22, log_content='flashback log content')

        ok_response = self.client.get(f'/api/execution-logs/flashback/{task.id}/log-content')
        self.assertEqual(ok_response.status_code, 200)
        self.assertEqual(ok_response.get_json()['data']['content'], 'flashback log content')

        with patch('services.flashback_service.open', side_effect=PermissionError('permission denied')):
            fail_response = self.client.get(f'/api/execution-logs/flashback/{task.id}/log-content')

        self.assertEqual(fail_response.status_code, 500)
        self.assertFalse(fail_response.get_json()['success'])
        self.assertIn('permission denied', fail_response.get_json()['error'])

    def test_archive_typed_log_content_supports_non_utf8_files(self):
        log = self._create_archive_log(task_id=50, log_id=50)
        with open(log.log_file, 'wb') as file_obj:
            file_obj.write('执行成功'.encode('gbk'))

        response = self.client.get(f'/api/execution-logs/archive/{log.id}/log-content')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertTrue(body['data']['has_file'])
        self.assertIn('执行成功', body['data']['content'])

    def test_flashback_typed_log_content_returns_empty_payload_while_task_is_waiting_for_log(self):
        task = self._create_flashback_task(task_id=23, status='queued', log_content=None)
        task.log_file = None
        db.session.commit()

        response = self.client.get(f'/api/execution-logs/flashback/{task.id}/log-content')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['content'], '')
        self.assertFalse(body['data']['has_file'])

    def test_flashback_artifact_download_rejects_tampered_manifest_path(self):
        rogue_artifact = os.path.join(self.escape_dir, 'escape.sql')
        task = self._create_flashback_task(
            task_id=21,
            artifacts=[{
                'id': 'result-sql',
                'path': rogue_artifact,
                'content': 'select 1;',
            }],
        )

        response = self.client.get(f'/api/flashback-tasks/{task.id}/artifacts/result-sql/download')

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()['success'])

    def test_flashback_artifact_download_returns_file_from_task_root(self):
        artifact_rel_path = os.path.join('output', 'result.sql')
        task = self._create_flashback_task(
            task_id=23,
            artifacts=[{
                'id': 'result-sql',
                'path': artifact_rel_path,
                'content': 'select 1;',
            }],
        )

        response = self.client.get(f'/api/flashback-tasks/{task.id}/artifacts/result-sql/download')

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))
        self.assertEqual(response.data.decode('utf-8'), 'select 1;')
        response.close()

    def test_flashback_task_detail_hides_artifact_paths(self):
        task = self._create_flashback_task(
            task_id=24,
            artifacts=[{
                'id': 'result-sql',
                'path': os.path.join('output', 'result.sql'),
                'content': 'select 1;',
            }],
        )

        response = self.client.get(f'/api/flashback-tasks/{task.id}')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertEqual(data['log_file'], None)
        self.assertEqual(data['artifacts'][0]['id'], 'result-sql')
        self.assertEqual(data['artifacts'][0]['name'], 'result.sql')
        self.assertEqual(data['artifacts'][0]['size'], len('select 1;'))
        self.assertNotIn('path', data['artifacts'][0])


if __name__ == '__main__':
    unittest.main()
