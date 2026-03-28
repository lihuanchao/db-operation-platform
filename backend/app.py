from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from config import Config
from extensions import db
from sqlalchemy import text
from datetime import datetime, timedelta
import io
import pymysql
import os

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)

# Import models after db initialization
from models.slow_sql import MonitorMysqlSlowQueryOptimized
from models.db_connection import DbConnection
from models import ArchiveTask, CronJob, ExecutionLog
from services.llm_service import LLMService
from services.sql_metadata_service import SQLMetadataService
from services.archive_service import ArchiveService
from services.cron_service import CronService
from services.execution_log_service import ExecutionLogService
from services.pt_archiver import PTArchiver
from services.scheduler_service import SchedulerService
from utils.downloader import Downloader

# 初始化定时任务调度器
with app.app_context():
    SchedulerService.initialize()


def success_response(data=None):
    return jsonify({'success': True, 'data': data})


def error_response(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code


@app.route('/api/slow-sqls', methods=['GET'])
def get_slow_sqls():
    # Get filter parameters
    database_name = request.args.get('database_name', '')
    host = request.args.get('host', '')
    is_optimized = request.args.get('is_optimized', '')
    time_range = request.args.get('time_range', '')
    ts_min = request.args.get('ts_min', '')
    ts_max = request.args.get('ts_max', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    slow_sqls = []
    total = 0

    # Calculate time range based on selection
    calculated_ts_min = ts_min
    calculated_ts_max = ts_max

    if time_range and time_range != 'custom':
        now = datetime.now()
        if time_range == '1h':
            calculated_ts_min = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
            calculated_ts_max = now.strftime('%Y-%m-%dT%H:%M')
        elif time_range == 'today':
            calculated_ts_min = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M')
            calculated_ts_max = now.strftime('%Y-%m-%dT%H:%M')
        elif time_range == '7d':
            calculated_ts_min = (now - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M')
            calculated_ts_max = now.strftime('%Y-%m-%dT%H:%M')
        elif time_range == '30d':
            calculated_ts_min = (now - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
            calculated_ts_max = now.strftime('%Y-%m-%dT%H:%M')

    try:
        # Build raw SQL query based on the user's provided SQL
        sql_query = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
    LEFT JOIN monitor_mysql_slow_query_optimized m ON a.checksum = m.checksum
WHERE
    c.host IS NOT NULL
    AND c.port IS NOT NULL
    AND c.is_delete != 1
    AND a.sample != 'commit'
    AND (b.db_max != 'information_schema' OR b.db_max IS NULL)
    AND b.user_max IS NOT NULL
"""

        params = {}

        # Add host filter
        if host:
            sql_query += ' AND c.host = :host'
            params['host'] = host

        # Add database filter
        if database_name:
            sql_query += ' AND b.db_max = :database_name'
            params['database_name'] = database_name

        # Add is_optimized filter
        if is_optimized == '1':
            sql_query += ' AND m.is_optimized = 1'
        elif is_optimized == '0':
            sql_query += ' AND (m.is_optimized = 0 OR m.is_optimized IS NULL)'

        # Add time range filter
        if calculated_ts_min and calculated_ts_max:
            try:
                t1 = datetime.fromisoformat(calculated_ts_min.replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(calculated_ts_max.replace('Z', '+00:00'))
                if t1 > t2:
                    t1, t2 = t2, t1
                sql_query += ' AND b.ts_min > :ts_min AND b.ts_max < :ts_max'
                params['ts_min'] = t1
                params['ts_max'] = t2
            except Exception as e:
                print(f"Time filter error: {e}")

        sql_query += """
GROUP BY
    a.checksum
ORDER BY
    SUM(b.Query_time_sum) DESC
"""

        # Execute query
        with db.engine.connect() as conn:
            # Get total count
            count_query = f'SELECT COUNT(*) FROM ({sql_query}) AS cnt'
            count_result = conn.execute(text(count_query), params)
            total = count_result.scalar() or 0

            # Get paginated results
            offset = (page - 1) * per_page
            paginated_query = sql_query + ' LIMIT :limit OFFSET :offset'
            params['limit'] = per_page
            params['offset'] = offset

            result = conn.execute(text(paginated_query), params)
            rows = result.fetchall()
            columns = result.keys()

            # Convert to list of dicts
            for row in rows:
                item = dict(zip(columns, row))
                # Get optimization suggestion
                opt = MonitorMysqlSlowQueryOptimized.query.get(item['checksum'])
                item['optimized_suggestion'] = opt.optimized_suggestion if opt else None
                item['is_optimized'] = opt.is_optimized if opt else 0
                slow_sqls.append(item)

    except Exception as e:
        return error_response(f"数据库连接或查询错误: {str(e)}", 500)

    total_pages = (total + per_page - 1) // per_page if total else 1

    return success_response({
        'items': slow_sqls,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
        }
    })


@app.route('/api/slow-sqls/<checksum>', methods=['GET'])
def get_slow_sql_detail(checksum):
    # Get the slow SQL data with ALL fields from the original query
    sql_query = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    b.user_max,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time,
    MAX(b.Query_time_max) AS max_time,
    MIN(b.Query_time_min) AS min_time,
    SUM(b.Query_time_sum) AS total_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE
    a.checksum = :checksum
GROUP BY
    a.checksum
"""

    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(sql_query), {'checksum': checksum})
            row = result.fetchone()
            if not row:
                return error_response("未找到该SQL记录", 404)

            columns = result.keys()
            slow_sql = dict(zip(columns, row))

            # Get optimization suggestion
            opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
            slow_sql['optimized_suggestion'] = opt.optimized_suggestion if opt else None
            slow_sql['is_optimized'] = opt.is_optimized if opt else 0

        return success_response(slow_sql)
    except Exception as e:
        return error_response(f"查询错误: {str(e)}", 500)


@app.route('/api/slow-sqls/<checksum>/optimize', methods=['POST'])
def optimize_slow_sql(checksum):
    try:
        # Get the SQL sample, host, and database name
        sample = None
        host = None
        database_name = None
        with db.engine.connect() as conn:
            sql_query = """
SELECT a.sample, c.host, b.db_max
FROM monitor_mysql_slow_query_review a
LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE a.checksum = :checksum
LIMIT 1
"""
            result = conn.execute(text(sql_query), {'checksum': checksum})
            row = result.fetchone()
            if not row or not row[0]:
                return error_response('SQL not found', 404)

            sample = row[0]
            host = row[1]
            database_name = row[2]

        # Find matching database connection
        db_connection = None
        if host:
            db_connections = DbConnection.query.filter(DbConnection.is_enabled != 0).all()
            metadata_service = SQLMetadataService()
            db_connection = metadata_service.get_connection_by_manage_host(db_connections, host)

        llm_service = LLMService()
        suggestion = llm_service.get_optimization_suggestion(sample, db_connection, host, database_name)

        # Save to monitor_mysql_slow_query_optimized
        opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
        if not opt:
            opt = MonitorMysqlSlowQueryOptimized(checksum=checksum)
        opt.optimized_suggestion = suggestion
        opt.is_optimized = 1
        db.session.add(opt)
        db.session.commit()

        return success_response({'suggestion': suggestion})
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/slow-sqls/batch-optimize', methods=['POST'])
def batch_optimize_slow_sqls():
    checksums = request.json.get('ids', [])
    if not checksums:
        return error_response('No checksums provided', 400)

    llm_service = LLMService()
    metadata_service = SQLMetadataService()
    # Get all enabled connections once
    db_connections = DbConnection.query.filter(DbConnection.is_enabled != 0).all()
    results = []

    for checksum in checksums:
        # Get the SQL sample, host, and database name
        sample = None
        host = None
        database_name = None
        sql_query = '''
SELECT a.sample, c.host, b.db_max
FROM monitor_mysql_slow_query_review a
LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE a.checksum = :checksum
LIMIT 1
'''
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text(sql_query), {'checksum': checksum})
                row = result.fetchone()
                if not row or not row[0]:
                    results.append({'id': checksum, 'success': False, 'error': 'Not found'})
                    continue

                sample = row[0]
                host = row[1]
                database_name = row[2]

            # Find matching database connection
            db_connection = None
            if host:
                db_connection = metadata_service.get_connection_by_manage_host(db_connections, host)

            suggestion = llm_service.get_optimization_suggestion(sample, db_connection, host, database_name)

            # Save to monitor_mysql_slow_query_optimized
            opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
            if not opt:
                opt = MonitorMysqlSlowQueryOptimized(checksum=checksum)
            opt.optimized_suggestion = suggestion
            opt.is_optimized = 1
            db.session.add(opt)
            results.append({'id': checksum, 'success': True, 'suggestion': suggestion})
        except Exception as e:
            results.append({'id': checksum, 'success': False, 'error': str(e)})

    db.session.commit()
    return success_response({'results': results})


@app.route('/api/slow-sqls/<checksum>/download', methods=['GET'])
def download_slow_sql(checksum):
    # Get data for download
    sql_query = """
SELECT
    a.checksum,
    b.db_max AS database_name,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
WHERE
    a.checksum = :checksum
GROUP BY
    a.checksum
"""

    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(sql_query), {'checksum': checksum})
            row = result.fetchone()
            if not row:
                return error_response("Not found", 404)

            columns = result.keys()
            data = dict(zip(columns, row))

            # Get optimization suggestion
            opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
            data['optimized_suggestion'] = opt.optimized_suggestion if opt else None

        # Create a simple object for the downloader
        class SimpleSlowSQL:
            def __init__(self, data):
                self.checksum = data['checksum']
                self.database_name = data['database_name']
                self.sql_text = data['sample']
                self.execution_time = data['avg_time']
                self.execution_count = data['execution_count']
                self.created_at = data['last_seen']
                self.optimized_suggestion = data['optimized_suggestion']

        markdown = Downloader.generate_markdown([SimpleSlowSQL(data)])

        return send_file(
            io.BytesIO(markdown.encode('utf-8')),
            mimetype='text/markdown',
            as_attachment=True,
            download_name=f'slow_sql_{checksum}_optimization.md'
        )
    except Exception as e:
        return error_response(f"下载错误: {str(e)}", 500)


@app.route('/api/slow-sqls/batch-download', methods=['POST'])
def batch_download_slow_sqls():
    checksums = request.json.get('ids', [])
    if not checksums:
        return error_response("No checksums provided", 400)

    # Get all data
    slow_sqls = []
    for checksum in checksums:
        sql_query = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE
    a.checksum = :checksum
GROUP BY
    a.checksum
"""

        try:
            with db.engine.connect() as conn:
                result = conn.execute(text(sql_query), {'checksum': checksum})
                row = result.fetchone()
                if row:
                    columns = result.keys()
                    data = dict(zip(columns, row))

                    # Get optimization suggestion
                    opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
                    data['optimized_suggestion'] = opt.optimized_suggestion if opt else None

                    # Create simple object
                    class SimpleSlowSQL:
                        def __init__(self, d):
                            self.checksum = d['checksum']
                            self.host = d['host']
                            self.database_name = d['database_name']
                            self.sample = d['sample']
                            self.execution_time = d['avg_time']
                            self.execution_count = d['execution_count']
                            self.last_seen = d['last_seen']
                            self.optimized_suggestion = d['optimized_suggestion']

                    slow_sqls.append(SimpleSlowSQL(data))
        except Exception as e:
            print(f"Error fetching {checksum}: {e}")
            continue

    csv_content = Downloader.generate_csv(slow_sqls)

    return send_file(
        io.BytesIO(csv_content.encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'slow_sql_batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )



@app.route('/api/connections', methods=['GET'])
def get_connections():
    """获取连接列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    connection_name = request.args.get('connection_name', '')
    host = request.args.get('host', '')

    query = DbConnection.query

    if connection_name:
        query = query.filter(DbConnection.connection_name.like(f'%{connection_name}%'))
    if host:
        query = query.filter(DbConnection.host.like(f'%{host}%'))

    total = query.count()
    connections = query.order_by(DbConnection.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    data = {
        'items': [conn.to_dict() for conn in connections.items],
        'total': total,
        'page': page,
        'per_page': per_page
    }

    return success_response(data)


@app.route('/api/connections', methods=['POST'])
def create_connection():
    """新增连接"""
    try:
        data = request.json
        required_fields = ['connection_name', 'host', 'port', 'username', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'{field} 是必填字段', 400)

        # Check if connection name already exists
        existing = DbConnection.query.filter(DbConnection.connection_name == data['connection_name']).first()
        if existing:
            return error_response('连接名称已存在', 400)

        connection = DbConnection(
            connection_name=data['connection_name'],
            host=data['host'],
            manage_host=data.get('manage_host'),
            port=data['port'],
            username=data['username'],
            password=data['password'],
            is_enabled=data.get('is_enabled', 1)
        )
        db.session.add(connection)
        db.session.commit()

        return success_response(connection.to_dict())
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建失败: {str(e)}', 500)


@app.route('/api/connections/<int:id>', methods=['GET'])
def get_connection(id):
    """获取单个连接"""
    connection = DbConnection.query.get(id)
    if not connection:
        return error_response('连接不存在', 404)

    return success_response(connection.to_dict())


@app.route('/api/connections/<int:id>', methods=['PUT'])
def update_connection(id):
    """更新连接"""
    try:
        connection = DbConnection.query.get(id)
        if not connection:
            return error_response('连接不存在', 404)

        data = request.json
        if 'connection_name' in data:
            # Only check for duplicates if the name is actually changing
            new_name = data['connection_name']
            if new_name != connection.connection_name:
                # Check if connection name already exists (excluding current)
                existing = DbConnection.query.filter(
                    DbConnection.connection_name == new_name,
                    DbConnection.id != id
                ).first()
                if existing:
                    return error_response('连接名称已存在', 400)
            connection.connection_name = new_name

        if 'host' in data:
            connection.host = data['host']
        if 'manage_host' in data:
            connection.manage_host = data['manage_host']
        if 'port' in data:
            connection.port = data['port']
        if 'username' in data:
            connection.username = data['username']
        if 'password' in data and data['password']:
            connection.password = data['password']
        if 'is_enabled' in data:
            connection.is_enabled = 1 if data['is_enabled'] else 0

        db.session.commit()
        return success_response(connection.to_dict())
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新失败: {str(e)}', 500)


@app.route('/api/connections/<int:id>', methods=['DELETE'])
def delete_connection(id):
    """删除连接"""
    try:
        connection = DbConnection.query.get(id)
        if not connection:
            return error_response('连接不存在', 404)

        connection.is_enabled = 0
        db.session.commit()
        return success_response({'id': id})
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除失败: {str(e)}', 500)


@app.route('/api/connections/test-direct', methods=['POST'])
def test_connection_direct():
    """直接测试连接信息（不保存到数据库）"""
    try:
        data = request.json
        required_fields = ['host', 'port', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return error_response(f'{field} 是必填字段', 400)

        # 测试连接
        conn = pymysql.connect(
            host=data['host'],
            port=int(data['port']),
            user=data['username'],
            password=data['password'],
            connect_timeout=5
        )
        conn.close()
        return success_response({'success': True, 'message': '连接成功'})
    except Exception as e:
        return error_response(f'连接失败: {str(e)}', 400)


@app.route('/api/connections/<int:id>/test', methods=['POST'])
def test_connection(id):
    """测试连接（通过已保存的连接ID）"""
    connection = DbConnection.query.get(id)
    if not connection:
        return error_response('连接不存在', 404)

    try:
        # 测试连接
        conn = pymysql.connect(
            host=connection.host,
            port=connection.port,
            user=connection.username,
            password=connection.password,
            connect_timeout=5
        )
        conn.close()
        return success_response({'success': True, 'message': '连接成功'})
    except Exception as e:
        return error_response(f'连接失败: {str(e)}', 400)


# ==================== 归档任务 API ====================

@app.route('/api/archive-tasks', methods=['GET'])
def get_archive_tasks():
    """获取归档任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_name = request.args.get('task_name', '')
    source_connection_id = request.args.get('source_connection_id', None, type=int)

    data = ArchiveService.get_task_list(page, per_page, task_name, source_connection_id)
    return success_response(data)


@app.route('/api/archive-tasks', methods=['POST'])
def create_archive_task():
    """创建归档任务"""
    try:
        data = request.json
        required_fields = ['task_name', 'source_connection_id', 'source_database', 'source_table', 'where_condition']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'{field} 是必填字段', 400)

        task, error = ArchiveService.create_task(data)
        if error:
            return error_response(error, 400)
        return success_response(task)
    except Exception as e:
        return error_response(f'创建失败: {str(e)}', 500)


@app.route('/api/archive-tasks/<int:id>', methods=['GET'])
def get_archive_task(id):
    """获取归档任务详情"""
    task = ArchiveService.get_task_detail(id)
    if not task:
        return error_response('任务不存在', 404)
    return success_response(task)


@app.route('/api/archive-tasks/<int:id>', methods=['PUT'])
def update_archive_task(id):
    """更新归档任务"""
    try:
        data = request.json
        task, error = ArchiveService.update_task(id, data)
        if error:
            return error_response(error, 400)
        return success_response(task)
    except Exception as e:
        return error_response(f'更新失败: {str(e)}', 500)


@app.route('/api/archive-tasks/<int:id>', methods=['DELETE'])
def delete_archive_task(id):
    """删除归档任务"""
    try:
        result, error = ArchiveService.delete_task(id)
        if error:
            return error_response(error, 400)
        return success_response(result)
    except Exception as e:
        return error_response(f'删除失败: {str(e)}', 500)


@app.route('/api/archive-tasks/<int:id>/execute', methods=['POST'])
def execute_archive_task(id):
    """立即执行归档任务（异步）"""
    try:
        task = ArchiveTask.query.get(id)
        if not task or task.is_enabled == 0:
            return error_response('任务不存在或已禁用', 404)

        # 创建执行日志，状态为执行中
        start_time = datetime.now()
        log_data = {
            'task_id': task.id,
            'start_time': start_time,
            'status': 2  # 执行中
        }
        log, log_error = ExecutionLogService.create_log(log_data)
        if log_error:
            return error_response(f'创建日志失败: {log_error}', 500)

        # 异步执行归档任务
        PTArchiver.execute_archive_async(task, log['id'])

        # 立即返回，提示任务已加入后台执行
        return success_response({'log_id': log['id'], 'message': '任务已加入后台执行', 'status': 'running'})

    except Exception as e:
        return error_response(f'执行失败: {str(e)}', 500)


# ==================== 定时任务 API ====================

@app.route('/api/cron-jobs', methods=['GET'])
def get_cron_jobs():
    """获取定时任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_id = request.args.get('task_id', None, type=int)

    data = CronService.get_job_list(page, per_page, task_id)
    return success_response(data)


@app.route('/api/cron-jobs', methods=['POST'])
def create_cron_job():
    """创建定时任务"""
    try:
        data = request.json
        required_fields = ['task_id', 'cron_expression']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'{field} 是必填字段', 400)

        job, error = CronService.create_job(data)
        if error:
            return error_response(error, 400)
        return success_response(job)
    except Exception as e:
        return error_response(f'创建失败: {str(e)}', 500)


@app.route('/api/cron-jobs/<int:id>', methods=['GET'])
def get_cron_job(id):
    """获取定时任务详情"""
    job = CronService.get_job_detail(id)
    if not job:
        return error_response('定时任务不存在', 404)
    return success_response(job)


@app.route('/api/cron-jobs/<int:id>', methods=['PUT'])
def update_cron_job(id):
    """更新定时任务"""
    try:
        data = request.json
        job, error = CronService.update_job(id, data)
        if error:
            return error_response(error, 400)
        return success_response(job)
    except Exception as e:
        return error_response(f'更新失败: {str(e)}', 500)


@app.route('/api/cron-jobs/<int:id>', methods=['DELETE'])
def delete_cron_job(id):
    """删除定时任务"""
    try:
        result, error = CronService.delete_job(id)
        if error:
            return error_response(error, 400)
        return success_response(result)
    except Exception as e:
        return error_response(f'删除失败: {str(e)}', 500)


@app.route('/api/cron-jobs/<int:id>/toggle', methods=['POST'])
def toggle_cron_job(id):
    """切换定时任务状态"""
    try:
        job, error = CronService.toggle_job(id)
        if error:
            return error_response(error, 400)
        return success_response(job)
    except Exception as e:
        return error_response(f'操作失败: {str(e)}', 500)


# ==================== 执行日志 API ====================

@app.route('/api/execution-logs', methods=['GET'])
def get_execution_logs():
    """获取执行日志列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_id = request.args.get('task_id', None, type=int)
    status = request.args.get('status', None, type=int)

    data = ExecutionLogService.get_log_list(page, per_page, task_id, status)
    return success_response(data)


@app.route('/api/execution-logs/<int:id>', methods=['GET'])
def get_execution_log(id):
    """获取执行日志详情"""
    log = ExecutionLogService.get_log_detail(id)
    if not log:
        return error_response('日志不存在', 404)
    return success_response(log)


@app.route('/api/execution-logs/<int:id>/download', methods=['GET'])
def download_execution_log(id):
    """下载执行日志文件"""
    log = ExecutionLog.query.get(id)
    if not log or not log.log_file:
        return error_response('日志文件不存在', 404)

    try:
        import os
        if os.path.exists(log.log_file):
            filename = os.path.basename(log.log_file)
            response = send_file(
                log.log_file,
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
            # 添加缓存控制头，防止浏览器缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return error_response('日志文件已被删除', 404)
    except Exception as e:
        return error_response(f'下载失败: {str(e)}', 500)


@app.route('/api/execution-logs/<int:id>/log-content', methods=['GET'])
def get_log_content(id):
    """获取执行日志的实时内容"""
    log = ExecutionLog.query.get(id)
    if not log:
        return error_response('执行日志不存在', 404)

    log_file = log.log_file
    if not log_file or not os.path.exists(log_file):
        return success_response({'content': '', 'has_file': False})

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return success_response({'content': content, 'has_file': True})
    except Exception as e:
        return error_response(f'读取日志失败: {str(e)}', 500)


@app.route('/api/health', methods=['GET'])
def health_check():
    return success_response({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
