from app import app
from extensions import db
from models.db_connection import DbConnection
from models import ArchiveTask, CronJob, ExecutionLog


def init_db():
    """初始化数据库 - 创建所有表"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功！")

        # 验证表是否创建成功
        from sqlalchemy import text
        tables_to_check = [
            'db_connection',
            'archive_task',
            'cron_job',
            'execution_log'
        ]

        for table_name in tables_to_check:
            try:
                result = db.session.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                if result.fetchone():
                    print(f"{table_name}表已成功创建！")
                else:
                    print(f"{table_name}表创建失败！")
            except Exception as e:
                print(f"检查{table_name}表状态时出错: {e}")


if __name__ == '__main__':
    init_db()
