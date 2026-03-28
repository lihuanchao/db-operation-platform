from models import ArchiveTask, DbConnection
from extensions import db


class ArchiveService:
    """
    归档任务服务
    """

    @staticmethod
    def get_task_list(page=1, per_page=10, task_name='', source_connection_id=None):
        """
        获取任务列表
        """
        query = ArchiveTask.query

        if task_name:
            query = query.filter(ArchiveTask.task_name.like(f'%{task_name}%'))

        if source_connection_id:
            query = query.filter(ArchiveTask.source_connection_id == source_connection_id)

        total = query.count()
        tasks = query.order_by(ArchiveTask.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': [task.to_dict() for task in tasks.items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def get_task_detail(task_id):
        """
        获取任务详情
        """
        task = ArchiveTask.query.get(task_id)
        if not task:
            return None
        return task.to_dict()

    @staticmethod
    def create_task(data):
        """
        创建归档任务
        """
        try:
            # 验证源库连接存在
            source_connection = DbConnection.query.get(data['source_connection_id'])
            if not source_connection or source_connection.is_enabled == 0:
                return None, '源库连接不存在或已禁用'

            dest_connection = None
            if data.get('dest_connection_id'):
                dest_connection = DbConnection.query.get(data['dest_connection_id'])
                if not dest_connection or dest_connection.is_enabled == 0:
                    return None, '目标库连接不存在或已禁用'

            task = ArchiveTask(
                task_name=data['task_name'],
                source_connection_id=data['source_connection_id'],
                source_database=data['source_database'],
                source_table=data['source_table'],
                dest_connection_id=data.get('dest_connection_id'),
                dest_database=data.get('dest_database'),
                dest_table=data.get('dest_table'),
                where_condition=data['where_condition'],
                is_enabled=data.get('is_enabled', 1)
            )

            db.session.add(task)
            db.session.commit()

            return task.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_task(task_id, data):
        """
        更新归档任务
        """
        try:
            task = ArchiveTask.query.get(task_id)
            if not task:
                return None, '任务不存在'

            if 'task_name' in data:
                task.task_name = data['task_name']

            if 'source_connection_id' in data:
                source_connection = DbConnection.query.get(data['source_connection_id'])
                if not source_connection or source_connection.is_enabled == 0:
                    return None, '源库连接不存在或已禁用'
                task.source_connection_id = data['source_connection_id']

            if 'source_database' in data:
                task.source_database = data['source_database']

            if 'source_table' in data:
                task.source_table = data['source_table']

            if 'dest_connection_id' in data:
                if data['dest_connection_id']:
                    dest_connection = DbConnection.query.get(data['dest_connection_id'])
                    if not dest_connection or dest_connection.is_enabled == 0:
                        return None, '目标库连接不存在或已禁用'
                task.dest_connection_id = data['dest_connection_id']

            if 'dest_database' in data:
                task.dest_database = data['dest_database']

            if 'dest_table' in data:
                task.dest_table = data['dest_table']

            if 'where_condition' in data:
                task.where_condition = data['where_condition']

            if 'is_enabled' in data:
                task.is_enabled = 1 if data['is_enabled'] else 0

            db.session.commit()

            return task.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_task(task_id):
        """
        删除归档任务
        """
        try:
            task = ArchiveTask.query.get(task_id)
            if not task:
                return None, '任务不存在'

            task.is_enabled = 0
            db.session.commit()

            return {'id': task_id}, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
