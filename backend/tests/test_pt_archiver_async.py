import os
import time
import unittest
from datetime import datetime
from unittest.mock import patch

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'pt-archiver-async-secret'

from app import app
from extensions import db
from models.archive_task import ArchiveTask
from models.db_connection import DbConnection
from models.execution_log import ExecutionLog
from services.pt_archiver import PTArchiver


class PTArchiverAsyncTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='pt-archiver-async-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        conn = DbConnection(
            id=1,
            connection_name='源库连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1,
        )
        task = ArchiveTask(
            id=1,
            task_name='订单归档任务',
            source_connection_id=1,
            source_database='demo_db',
            source_table='orders',
            where_condition='id > 0',
            is_enabled=1,
        )
        log = ExecutionLog(
            id=1,
            task_id=1,
            start_time=datetime.now(),
            status=2,
            log_file=None,
            error_message=None,
        )

        db.session.add_all([conn, task, log])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _wait_log_update(self, log_id, timeout_seconds=1.5):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            db.session.remove()
            log = ExecutionLog.query.get(log_id)
            if log and log.status != 2:
                return log
            time.sleep(0.05)

        db.session.remove()
        return ExecutionLog.query.get(log_id)

    def test_async_worker_exception_marks_log_failed(self):
        task = ArchiveTask.query.get(1)
        self.assertIsNotNone(task)

        with patch(
            'services.pt_archiver.PTArchiver.build_source_str',
            side_effect=RuntimeError('mock build_source_str failure')
        ):
            PTArchiver.execute_archive_async(task, 1)
            updated_log = self._wait_log_update(1)

        self.assertIsNotNone(updated_log)
        self.assertEqual(updated_log.status, 0)
        self.assertIsNotNone(updated_log.end_time)
        self.assertIn('mock build_source_str failure', updated_log.error_message or '')


if __name__ == '__main__':
    unittest.main()
