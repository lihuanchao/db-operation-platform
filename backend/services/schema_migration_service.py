from sqlalchemy import inspect, text

from extensions import db
from models.login_log import LoginLog
from models.optimization_task import OptimizationTask
from models.sys_user import SysUser
from models.user_connection_permission import UserConnectionPermission


class SchemaMigrationService:
    REQUIRED_OPTIMIZATION_COLUMNS = {
        'creator_user_id': 'ALTER TABLE optimization_task ADD COLUMN creator_user_id BIGINT NULL',
        'creator_employee_no': 'ALTER TABLE optimization_task ADD COLUMN creator_employee_no VARCHAR(32) NULL',
        'connection_id': 'ALTER TABLE optimization_task ADD COLUMN connection_id BIGINT NULL',
        'database_name': 'ALTER TABLE optimization_task ADD COLUMN database_name VARCHAR(100) NULL',
    }

    @classmethod
    def ensure_auth_schema(cls):
        OptimizationTask.__table__.create(bind=db.engine, checkfirst=True)
        SysUser.__table__.create(bind=db.engine, checkfirst=True)
        UserConnectionPermission.__table__.create(bind=db.engine, checkfirst=True)
        LoginLog.__table__.create(bind=db.engine, checkfirst=True)

        inspector = inspect(db.engine)
        existing_columns = {
            column['name'] for column in inspector.get_columns('optimization_task')
        }

        for name, ddl in cls.REQUIRED_OPTIMIZATION_COLUMNS.items():
            if name in existing_columns:
                continue
            db.session.execute(text(ddl))

        db.session.commit()
