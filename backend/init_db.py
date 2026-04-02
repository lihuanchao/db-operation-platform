from app import app
from extensions import db
from models.db_connection import DbConnection
from models import ArchiveTask, CronJob, ExecutionLog, OptimizationTask
from services.schema_migration_service import SchemaMigrationService


def init_db():
    """初始化数据库 - 创建所有表"""
    with app.app_context():
        db.create_all()
        SchemaMigrationService.ensure_auth_schema()
        print("数据库表创建成功！")

        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        tables_to_check = [
            'db_connection',
            'archive_task',
            'cron_job',
            'execution_log',
            'optimization_task',
            'sys_user',
            'sys_user_connection_permission',
            'sys_login_log'
        ]

        for table_name in tables_to_check:
            if table_name in existing_tables:
                print(f"{table_name}表已成功创建！")
            else:
                print(f"{table_name}表创建失败！")


if __name__ == '__main__':
    init_db()
