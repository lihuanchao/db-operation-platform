import os
import shutil
import tempfile
import unittest
from datetime import datetime

from models.flashback_task import FlashbackTask
from services.flashback_service import FlashbackService


class FlashbackServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.output_dir = tempfile.mkdtemp(prefix='flashback-output-')

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _make_task(self, **kwargs):
        data = {
            'database_name': 'demo_db',
            'table_name': 'orders',
            'mode': 'repl',
            'sql_type': 'delete',
            'work_type': '2sql',
            'start_datetime': '2026-04-08 08:00:00',
            'stop_datetime': '2026-04-08 08:40:00',
            'start_file': 'mysql-bin.000001',
            'stop_file': 'mysql-bin.000002',
        }
        data.update(kwargs)
        return FlashbackTask(**data)

    def _make_connection(self):
        return type(
            'Connection',
            (),
            {
                'host': '10.0.0.1',
                'port': 3306,
                'username': 'repl',
                'password': 'secret',
            },
        )()

    def test_build_command_constructs_my2sql_command(self):
        task = self._make_task()

        command, masked_command = FlashbackService.build_command(task, self._make_connection(), self.output_dir)

        self.assertEqual(command, [
            FlashbackService.TOOL_PATH,
            '-databases', 'demo_db',
            '-tables', 'orders',
            '-mode', 'repl',
            '-host', '10.0.0.1',
            '-port', '3306',
            '-user', 'repl',
            '-password', 'secret',
            '-sql', 'delete',
            '-start-datetime', '2026-04-08 08:00:00',
            '-stop-datetime', '2026-04-08 08:40:00',
            '-start-file', 'mysql-bin.000001',
            '-stop-file', 'mysql-bin.000002',
            '-work-type', '2sql',
            '-output-dir', self.output_dir,
        ])
        self.assertEqual(
            masked_command,
            '/my2sql -databases demo_db -tables orders -mode repl -host 10.0.0.1 -port 3306 -user repl '
            '-password ****** -sql delete -start-datetime 2026-04-08 08:00:00 -stop-datetime 2026-04-08 08:40:00 '
            '-start-file mysql-bin.000001 -stop-file mysql-bin.000002 -work-type 2sql -output-dir '
            f'{self.output_dir}',
        )

    def test_build_command_skips_empty_start_and_stop_file(self):
        task = self._make_task(start_file='', stop_file='')

        command, _ = FlashbackService.build_command(task, self._make_connection(), self.output_dir)

        self.assertNotIn('-start-file', command)
        self.assertNotIn('-stop-file', command)

    def test_masked_command_hides_password_value(self):
        task = self._make_task()

        _, masked_command = FlashbackService.build_command(task, self._make_connection(), self.output_dir)

        self.assertNotIn('secret', masked_command)
        self.assertIn('******', masked_command)

    def test_collect_artifacts_returns_fixed_files_and_first_sql_file(self):
        paths = [
            os.path.join(self.output_dir, 'binlog_status.txt'),
            os.path.join(self.output_dir, 'biglong_trx.txt'),
            os.path.join(self.output_dir, 'c.sql'),
            os.path.join(self.output_dir, 'a.sql'),
            os.path.join(self.output_dir, 'b.sql'),
            os.path.join(self.output_dir, 'ignore.log'),
        ]
        for path in paths:
            with open(path, 'w', encoding='utf-8') as file_obj:
                file_obj.write(os.path.basename(path))

        artifacts = FlashbackService.collect_artifacts(self.output_dir)

        self.assertEqual(artifacts, [
            {
                'id': 'binlog_status',
                'name': 'binlog_status.txt',
                'path': os.path.join(self.output_dir, 'binlog_status.txt'),
                'size': len('binlog_status.txt'),
            },
            {
                'id': 'biglong_trx',
                'name': 'biglong_trx.txt',
                'path': os.path.join(self.output_dir, 'biglong_trx.txt'),
                'size': len('biglong_trx.txt'),
            },
            {
                'id': 'result-sql',
                'name': 'a.sql',
                'path': os.path.join(self.output_dir, 'a.sql'),
                'size': len('a.sql'),
            },
        ])

    def test_collect_artifacts_raises_when_fixed_file_missing(self):
        with open(os.path.join(self.output_dir, 'binlog_status.txt'), 'w', encoding='utf-8') as file_obj:
            file_obj.write('ok')

        with self.assertRaises(FileNotFoundError):
            FlashbackService.collect_artifacts(self.output_dir)

    def test_collect_artifacts_raises_when_sql_file_missing(self):
        with open(os.path.join(self.output_dir, 'binlog_status.txt'), 'w', encoding='utf-8') as file_obj:
            file_obj.write('ok')
        with open(os.path.join(self.output_dir, 'biglong_trx.txt'), 'w', encoding='utf-8') as file_obj:
            file_obj.write('ok')

        with self.assertRaises(FileNotFoundError):
            FlashbackService.collect_artifacts(self.output_dir)

    def test_flashback_task_artifact_serialization_round_trip(self):
        task = FlashbackTask(
            db_connection_id=1,
            connection_id=1,
            connection_name='测试连接',
            database_name='demo_db',
            table_name='orders',
            mode='repl',
            sql_type='delete',
            work_type='2sql',
            created_at=datetime(2026, 4, 8, 8, 1, 2),
            updated_at=datetime(2026, 4, 8, 8, 3, 4),
            started_at=datetime(2026, 4, 8, 8, 5, 6),
            finished_at=datetime(2026, 4, 8, 8, 7, 8),
        )

        artifacts = [
            {'id': 'binlog_status', 'name': 'binlog_status.txt', 'path': '/tmp/binlog_status.txt', 'size': 12},
            {'id': 'result-sql', 'name': 'a.sql', 'path': '/tmp/a.sql', 'size': 34},
        ]
        task.set_artifacts(artifacts)

        self.assertEqual(task.get_artifacts(), artifacts)
        self.assertEqual(task.to_dict()['artifacts'], artifacts)
        self.assertEqual(task.to_dict()['created_at'], '2026-04-08 08:01:02')
        self.assertEqual(task.to_dict()['updated_at'], '2026-04-08 08:03:04')
        self.assertEqual(task.to_dict()['started_at'], '2026-04-08 08:05:06')
        self.assertEqual(task.to_dict()['finished_at'], '2026-04-08 08:07:08')


if __name__ == '__main__':
    unittest.main()
