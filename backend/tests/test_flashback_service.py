import os
import shutil
import tempfile
import unittest

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

        self.assertEqual(command[0], FlashbackService.TOOL_PATH)
        self.assertIn('-databases', command)
        self.assertIn('-tables', command)
        self.assertIn('-mode', command)
        self.assertIn('-sql', command)
        self.assertIn('-work-type', command)
        self.assertIn('-output-dir', command)
        self.assertIn(self.output_dir, command)
        self.assertEqual(masked_command.count(FlashbackService.TOOL_PATH), 1)

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

        self.assertEqual([artifact['name'] for artifact in artifacts], [
            'binlog_status.txt',
            'biglong_trx.txt',
            'a.sql',
        ])


if __name__ == '__main__':
    unittest.main()
