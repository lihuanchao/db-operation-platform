from extensions import db
from models.slow_sql import SlowSQL
from datetime import datetime


class SlowSQLService:
    @staticmethod
    def get_all(database_name=None, system_name=None, page=1, per_page=10):
        query = SlowSQL.query
        if database_name:
            query = query.filter(SlowSQL.database_name.contains(database_name))
        if system_name:
            query = query.filter(SlowSQL.system_name.contains(system_name))
        return query.order_by(SlowSQL.created_at.desc()).paginate(page=page, per_page=per_page)

    @staticmethod
    def get_by_id(id):
        return SlowSQL.query.get(id)

    @staticmethod
    def create(database_name, system_name, sql_text, execution_time, execution_count=1):
        slow_sql = SlowSQL(
            database_name=database_name,
            system_name=system_name,
            sql_text=sql_text,
            execution_time=execution_time,
            execution_count=execution_count,
            created_at=datetime.utcnow()
        )
        db.session.add(slow_sql)
        db.session.commit()
        return slow_sql

    @staticmethod
    def update_suggestion(id, suggestion):
        slow_sql = SlowSQL.query.get(id)
        if slow_sql:
            slow_sql.optimized_suggestion = suggestion
            db.session.commit()
            return slow_sql
        return None

    @staticmethod
    def delete(id):
        slow_sql = SlowSQL.query.get(id)
        if slow_sql:
            db.session.delete(slow_sql)
            db.session.commit()
            return True
        return False
