import os
import unittest
from sqlalchemy import inspect

os.environ['USE_SQLITE'] = 'true'

from app import app
from extensions import db
from services.schema_migration_service import SchemaMigrationService


class SchemaMigrationServiceTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_ensure_auth_schema_creates_tables_and_columns(self):
        SchemaMigrationService.ensure_auth_schema()

        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        self.assertIn('sys_user', table_names)
        self.assertIn('sys_user_connection_permission', table_names)
        self.assertIn('sys_login_log', table_names)

        optimization_columns = {
            column['name'] for column in inspector.get_columns('optimization_task')
        }
        self.assertIn('creator_user_id', optimization_columns)
        self.assertIn('creator_employee_no', optimization_columns)
        self.assertIn('connection_id', optimization_columns)
        self.assertIn('database_name', optimization_columns)

    def test_ensure_sql_throttle_schema_creates_tables(self):
        SchemaMigrationService.ensure_sql_throttle_schema()

        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        self.assertIn('sql_throttle_rule', table_names)
        self.assertIn('sql_throttle_run', table_names)
        self.assertIn('sql_throttle_kill_log', table_names)
        self.assertIn('sql_throttle_fingerprint_state', table_names)


if __name__ == '__main__':
    unittest.main()
