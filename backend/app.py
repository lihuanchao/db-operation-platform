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
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)
CORS(app, supports_credentials=True)
db.init_app(app)

# Import models after db initialization
from models.slow_sql import MonitorMysqlSlowQueryOptimized
from models.db_connection import DbConnection
from models import ArchiveTask, CronJob, ExecutionLog
from models.sql_throttle_rule import SqlThrottleRule
from models.sql_throttle_run import SqlThrottleRun
from models.sql_throttle_kill_log import SqlThrottleKillLog
from services.llm_service import LLMService
from services.sql_metadata_service import SQLMetadataService
from services.archive_service import ArchiveService
from services.cron_service import CronService
from services.execution_log_service import ExecutionLogService
from services.flashback_service import FlashbackService
from services.optimization_task_service import OptimizationTaskService
from services.pt_archiver import PTArchiver
from services.scheduler_service import SchedulerService
from services.sql_throttle_rule_service import SqlThrottleRuleService
from services.sql_throttle_scheduler_service import SqlThrottleSchedulerService
from services.auth_service import AuthService
from services.access_control_service import AccessControlService, login_required, admin_required
from services.user_admin_service import UserAdminService
from services.slow_sql_query_service import SlowSqlQueryService
from utils.downloader import Downloader

# 初始化定时任务调度器
if os.environ.get('SKIP_SCHEDULER_INIT', '0') != '1':
    with app.app_context():
        SchedulerService.initialize()
        SqlThrottleSchedulerService.initialize()


def success_response(data=None):
    return jsonify({'success': True, 'data': data})


def error_response(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code


def _flashback_error_status(message):
    if '必填字段' in message or '不存在或已禁用' in message or '必须为整数' in message:
        return 400
    return 500


def get_request_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr


def parse_bool_param(value):
    if isinstance(value, bool):
        return value
    raw = (value or '').strip().lower()
    if raw in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if raw in ('0', 'false', 'no', 'n', 'off'):
        return False
    return None


def calculate_slow_sql_time_range(time_range, ts_min, ts_max):
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

    parsed_ts_min = None
    parsed_ts_max = None
    if calculated_ts_min and calculated_ts_max:
        try:
            parsed_ts_min = datetime.fromisoformat(calculated_ts_min.replace('Z', '+00:00'))
            parsed_ts_max = datetime.fromisoformat(calculated_ts_max.replace('Z', '+00:00'))
            if parsed_ts_min > parsed_ts_max:
                parsed_ts_min, parsed_ts_max = parsed_ts_max, parsed_ts_min
        except Exception:
            parsed_ts_min = None
            parsed_ts_max = None
    return parsed_ts_min, parsed_ts_max


def get_slow_sql_record(checksum, allowed_hosts=None):
    sql_query, params = SlowSqlQueryService.build_detail_query(checksum, allowed_hosts=allowed_hosts)
    with db.engine.connect() as conn:
        result = conn.execute(text(sql_query), params)
        row = result.fetchone()
        if not row:
            return None
        columns = result.keys()
        return dict(zip(columns, row))


@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    employee_no = (payload.get('employee_no') or '').strip()
    password = payload.get('password') or ''
    if not employee_no or not password:
        return error_response('工号和密码不能为空', 400)

    data, error = AuthService.login(
        employee_no=employee_no,
        password=password,
        ip=get_request_ip(),
        user_agent=request.headers.get('User-Agent', '')
    )
    if error:
        message, status_code = error
        return error_response(message, status_code)
    return success_response(data)


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout(current_user):
    AuthService.logout()
    return success_response({'logged_out': True})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def me(current_user):
    return success_response(AuthService.build_auth_payload(current_user))


@app.route('/api/auth/connections', methods=['GET'])
@login_required
def list_authorized_connections(current_user):
    if current_user.role_code == 'admin':
        connections = DbConnection.query.filter(DbConnection.is_enabled != 0).order_by(DbConnection.updated_at.desc()).all()
    else:
        connection_ids = UserAdminService.list_connection_permissions(current_user.id)
        if not connection_ids:
            connections = []
        else:
            connections = DbConnection.query.filter(
                DbConnection.is_enabled != 0,
                DbConnection.id.in_(connection_ids)
            ).order_by(DbConnection.updated_at.desc()).all()
    return success_response({'items': [item.to_dict() for item in connections]})


@app.route('/api/slow-sqls', methods=['GET'])
@login_required
def get_slow_sqls(current_user):
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

    parsed_ts_min, parsed_ts_max = calculate_slow_sql_time_range(time_range, ts_min, ts_max)
    allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)

    try:
        sql_query, params = SlowSqlQueryService.build_list_query({
            'database_name': database_name,
            'host': host,
            'is_optimized': is_optimized,
            'ts_min': parsed_ts_min,
            'ts_max': parsed_ts_max,
        }, allowed_hosts=allowed_hosts)

        with db.engine.connect() as conn:
            count_query = f'SELECT COUNT(*) FROM ({sql_query}) AS cnt'
            count_result = conn.execute(text(count_query), params)
            total = count_result.scalar() or 0

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
@login_required
def get_slow_sql_detail(current_user, checksum):
    try:
        allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)
        slow_sql = get_slow_sql_record(checksum, allowed_hosts=allowed_hosts)
        if not slow_sql:
            return error_response("未找到该SQL记录", 404)

        opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
        slow_sql['optimized_suggestion'] = opt.optimized_suggestion if opt else None
        slow_sql['is_optimized'] = opt.is_optimized if opt else 0
        slow_sql['writing_optimization'] = ''
        slow_sql['index_recommendation'] = ''
        slow_sql['optimized_content'] = None
        slow_sql['matched_rules'] = ''

        if slow_sql['optimized_suggestion']:
            writing_optimization, index_recommendation, optimized_content, matched_rules = OptimizationTaskService.extract_sections(
                slow_sql['optimized_suggestion']
            )
            slow_sql['writing_optimization'] = writing_optimization
            slow_sql['index_recommendation'] = index_recommendation
            slow_sql['optimized_content'] = optimized_content
            slow_sql['matched_rules'] = matched_rules

        return success_response(slow_sql)
    except Exception as e:
        return error_response(f"查询错误: {str(e)}", 500)


@app.route('/api/slow-sqls/<checksum>/optimize', methods=['POST'])
@login_required
def optimize_slow_sql(current_user, checksum):
    try:
        allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)
        slow_sql = get_slow_sql_record(checksum, allowed_hosts=allowed_hosts)
        if not slow_sql or not slow_sql.get('sample'):
            return error_response('SQL not found', 404)

        sample = slow_sql['sample']
        host = slow_sql['host']
        database_name = slow_sql['database_name']

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

        writing_optimization, index_recommendation, optimized_content, matched_rules = OptimizationTaskService.extract_sections(
            suggestion
        )

        return success_response({
            'suggestion': suggestion,
            'writing_optimization': writing_optimization,
            'index_recommendation': index_recommendation,
            'optimized_content': optimized_content,
            'matched_rules': matched_rules
        })
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/slow-sqls/batch-optimize', methods=['POST'])
@login_required
def batch_optimize_slow_sqls(current_user):
    checksums = (request.get_json(silent=True) or {}).get('ids', [])
    if not checksums:
        return error_response('No checksums provided', 400)

    llm_service = LLMService()
    metadata_service = SQLMetadataService()
    db_connections = DbConnection.query.filter(DbConnection.is_enabled != 0).all()
    allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)
    results = []

    for checksum in checksums:
        try:
            slow_sql = get_slow_sql_record(checksum, allowed_hosts=allowed_hosts)
            if not slow_sql or not slow_sql.get('sample'):
                results.append({'id': checksum, 'success': False, 'error': 'Not found'})
                continue

            sample = slow_sql['sample']
            host = slow_sql['host']
            database_name = slow_sql['database_name']

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
@login_required
def download_slow_sql(current_user, checksum):
    try:
        allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)
        data = get_slow_sql_record(checksum, allowed_hosts=allowed_hosts)
        if not data:
            return error_response("Not found", 404)

        opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
        data['optimized_suggestion'] = opt.optimized_suggestion if opt else None

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
@login_required
def batch_download_slow_sqls(current_user):
    checksums = (request.get_json(silent=True) or {}).get('ids', [])
    if not checksums:
        return error_response("No checksums provided", 400)

    allowed_hosts = AccessControlService.authorized_manage_hosts(current_user)
    slow_sqls = []
    for checksum in checksums:
        try:
            data = get_slow_sql_record(checksum, allowed_hosts=allowed_hosts)
            if not data:
                continue

            opt = MonitorMysqlSlowQueryOptimized.query.get(checksum)
            data['optimized_suggestion'] = opt.optimized_suggestion if opt else None

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


# ==================== SQL优化建议任务 API ====================

@app.route('/api/optimization-tasks', methods=['GET'])
@login_required
def get_optimization_tasks(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_type = request.args.get('task_type', '')
    data = OptimizationTaskService.get_task_list(page, per_page, task_type, current_user=current_user)
    return success_response(data)


@app.route('/api/optimization-tasks/sql', methods=['POST'])
@login_required
def create_sql_optimization_task(current_user):
    try:
        data = request.get_json(silent=True) or {}
        required_fields = ['db_connection_id', 'database_name', 'sql_text']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'{field} 是必填字段', 400)

        task, error = OptimizationTaskService.create_task(
            task_type='sql',
            db_connection_id=int(data['db_connection_id']),
            database_name=data['database_name'],
            object_content=data['sql_text'],
            current_user=current_user
        )
        if error:
            return error_response(error, 400)
        return success_response(task)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception as e:
        return error_response(f'创建SQL优化任务失败: {str(e)}', 500)


@app.route('/api/optimization-tasks/mybatis', methods=['POST'])
@login_required
def create_mybatis_optimization_task(current_user):
    try:
        data = request.get_json(silent=True) or {}
        required_fields = ['db_connection_id', 'database_name', 'xml_text']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'{field} 是必填字段', 400)

        task, error = OptimizationTaskService.create_task(
            task_type='mybatis',
            db_connection_id=int(data['db_connection_id']),
            database_name=data['database_name'],
            object_content=data['xml_text'],
            current_user=current_user
        )
        if error:
            return error_response(error, 400)
        return success_response(task)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception as e:
        return error_response(f'创建MyBatis优化任务失败: {str(e)}', 500)


@app.route('/api/optimization-tasks/<int:id>', methods=['GET'])
@login_required
def get_optimization_task_detail(current_user, id):
    task = OptimizationTaskService.get_task_detail(id, current_user=current_user)
    if not task:
        return error_response('优化任务不存在', 404)
    return success_response(task)


@app.route('/api/flashback-tasks', methods=['GET'])
@admin_required
def get_flashback_tasks(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    database_name = request.args.get('database_name', '')
    table_name = request.args.get('table_name', '')
    status = request.args.get('status', '')
    sql_type = request.args.get('sql_type', '')
    work_type = request.args.get('work_type', '')

    data = FlashbackService.get_task_list(
        page=page,
        per_page=per_page,
        database_name=database_name,
        table_name=table_name,
        status=status,
        sql_type=sql_type,
        work_type=work_type,
    )
    return success_response(data)


@app.route('/api/flashback-tasks', methods=['POST'])
@admin_required
def create_flashback_task(current_user):
    payload = request.get_json(silent=True) or {}
    required_fields = ['db_connection_id', 'database_name', 'table_name', 'sql_type', 'work_type']
    for field in required_fields:
        if field not in payload or not payload[field]:
            return error_response(f'{field} 是必填字段', 400)

    task, error = FlashbackService.create_task(payload, current_user=current_user)
    if error:
        return error_response(error, _flashback_error_status(error))
    return success_response(task)


@app.route('/api/flashback-tasks/<int:id>', methods=['GET'])
@admin_required
def get_flashback_task_detail(current_user, id):
    task = FlashbackService.get_task_detail(id)
    if not task:
        return error_response('任务不存在', 404)
    return success_response(task)


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users(current_user):
    return success_response({'items': UserAdminService.list_users()})


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def admin_create_user(current_user):
    payload = request.get_json(silent=True) or {}
    try:
        user = UserAdminService.create_user(payload, current_user.id)
    except ValueError as e:
        return error_response(str(e), 400)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def admin_update_user(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    try:
        user = UserAdminService.update_user(user_id, payload, current_user.id)
    except LookupError as e:
        return error_response(str(e), 404)
    except ValueError as e:
        return error_response(str(e), 400)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def admin_update_user_status(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    try:
        user = UserAdminService.update_status(user_id, payload.get('status'), current_user.id)
    except LookupError as e:
        return error_response(str(e), 404)
    except ValueError as e:
        return error_response(str(e), 400)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['PUT'])
@admin_required
def admin_reset_user_password(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    try:
        user = UserAdminService.reset_password(user_id, payload.get('password'), current_user.id)
    except LookupError as e:
        return error_response(str(e), 404)
    except ValueError as e:
        return error_response(str(e), 400)
    return success_response(user.to_dict())


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(current_user, user_id):
    try:
        UserAdminService.soft_delete_user(user_id, current_user.id)
    except LookupError as e:
        return error_response(str(e), 404)
    return success_response({'deleted': True})


@app.route('/api/admin/roles', methods=['GET'])
@admin_required
def admin_list_roles(current_user):
    return success_response(UserAdminService.FIXED_ROLES)


@app.route('/api/admin/user-connection-permissions/<int:user_id>', methods=['GET'])
@admin_required
def get_user_connection_permissions(current_user, user_id):
    return success_response({'connection_ids': UserAdminService.list_connection_permissions(user_id)})


@app.route('/api/admin/user-connection-permissions/<int:user_id>', methods=['PUT'])
@admin_required
def replace_user_connection_permissions(current_user, user_id):
    payload = request.get_json(silent=True) or {}
    try:
        connection_ids = UserAdminService.replace_connection_permissions(
            user_id,
            payload.get('connection_ids', []),
            current_user.id
        )
    except LookupError as e:
        return error_response(str(e), 404)
    return success_response({'connection_ids': connection_ids})



@app.route('/api/connections', methods=['GET'])
@admin_required
def get_connections(current_user):
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
@admin_required
def create_connection(current_user):
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
@admin_required
def get_connection(current_user, id):
    """获取单个连接"""
    connection = DbConnection.query.get(id)
    if not connection:
        return error_response('连接不存在', 404)

    return success_response(connection.to_dict())


@app.route('/api/connections/<int:id>', methods=['PUT'])
@admin_required
def update_connection(current_user, id):
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
@admin_required
def delete_connection(current_user, id):
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
@admin_required
def test_connection_direct(current_user):
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
@admin_required
def test_connection(current_user, id):
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
@admin_required
def get_archive_tasks(current_user):
    """获取归档任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_name = request.args.get('task_name', '')
    source_connection_id = request.args.get('source_connection_id', None, type=int)

    data = ArchiveService.get_task_list(page, per_page, task_name, source_connection_id)
    return success_response(data)


@app.route('/api/archive-tasks', methods=['POST'])
@admin_required
def create_archive_task(current_user):
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
@admin_required
def get_archive_task(current_user, id):
    """获取归档任务详情"""
    task = ArchiveService.get_task_detail(id)
    if not task:
        return error_response('任务不存在', 404)
    return success_response(task)


@app.route('/api/archive-tasks/<int:id>', methods=['PUT'])
@admin_required
def update_archive_task(current_user, id):
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
@admin_required
def delete_archive_task(current_user, id):
    """删除归档任务"""
    try:
        result, error = ArchiveService.delete_task(id)
        if error:
            return error_response(error, 400)
        return success_response(result)
    except Exception as e:
        return error_response(f'删除失败: {str(e)}', 500)


@app.route('/api/archive-tasks/<int:id>/execute', methods=['POST'])
@admin_required
def execute_archive_task(current_user, id):
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
@admin_required
def get_cron_jobs(current_user):
    """获取定时任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_id = request.args.get('task_id', None, type=int)

    data = CronService.get_job_list(page, per_page, task_id)
    return success_response(data)


@app.route('/api/cron-jobs', methods=['POST'])
@admin_required
def create_cron_job(current_user):
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
@admin_required
def get_cron_job(current_user, id):
    """获取定时任务详情"""
    job = CronService.get_job_detail(id)
    if not job:
        return error_response('定时任务不存在', 404)
    return success_response(job)


@app.route('/api/cron-jobs/<int:id>', methods=['PUT'])
@admin_required
def update_cron_job(current_user, id):
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
@admin_required
def delete_cron_job(current_user, id):
    """删除定时任务"""
    try:
        result, error = CronService.delete_job(id)
        if error:
            return error_response(error, 400)
        return success_response(result)
    except Exception as e:
        return error_response(f'删除失败: {str(e)}', 500)


@app.route('/api/cron-jobs/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_cron_job(current_user, id):
    """切换定时任务状态"""
    try:
        job, error = CronService.toggle_job(id)
        if error:
            return error_response(error, 400)
        return success_response(job)
    except Exception as e:
        return error_response(f'操作失败: {str(e)}', 500)


# ==================== SQL 限流 API ====================

@app.route('/api/sql-throttle-rules', methods=['GET'])
@admin_required
def get_sql_throttle_rules(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    rule_name = request.args.get('rule_name', '')
    enabled = parse_bool_param(request.args.get('enabled'))
    db_connection_id = request.args.get('db_connection_id', None, type=int)
    data = SqlThrottleRuleService.list_rules(
        page=page,
        per_page=per_page,
        rule_name=rule_name,
        enabled=enabled,
        db_connection_id=db_connection_id,
    )
    return success_response(data)


@app.route('/api/sql-throttle-rules', methods=['POST'])
@admin_required
def create_sql_throttle_rule(current_user):
    payload = request.get_json(silent=True) or {}
    item, error = SqlThrottleRuleService.create_rule(payload, current_user)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>', methods=['GET'])
@admin_required
def get_sql_throttle_rule(current_user, id):
    item = SqlThrottleRuleService.get_rule_detail(id)
    if not item:
        return error_response('规则不存在', 404)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>', methods=['PUT'])
@admin_required
def update_sql_throttle_rule(current_user, id):
    payload = request.get_json(silent=True) or {}
    item, error = SqlThrottleRuleService.update_rule(id, payload)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>', methods=['DELETE'])
@admin_required
def delete_sql_throttle_rule(current_user, id):
    item, error = SqlThrottleRuleService.delete_rule(id)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>/enable', methods=['POST'])
@admin_required
def enable_sql_throttle_rule(current_user, id):
    item, error = SqlThrottleRuleService.enable_rule(id)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>/disable', methods=['POST'])
@admin_required
def disable_sql_throttle_rule(current_user, id):
    item, error = SqlThrottleRuleService.disable_rule(id)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-rules/<int:id>/run-once', methods=['POST'])
@admin_required
def run_once_sql_throttle_rule(current_user, id):
    item, error = SqlThrottleRuleService.run_once(id)
    if error:
        return error_response(error, 400)
    return success_response(item)


@app.route('/api/sql-throttle-runs', methods=['GET'])
@admin_required
def get_sql_throttle_runs(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    rule_id = request.args.get('rule_id', None, type=int)
    rule_name = (request.args.get('rule_name') or '').strip()
    status = (request.args.get('status') or '').strip()
    is_hit = parse_bool_param(request.args.get('is_hit'))

    query = SqlThrottleRun.query
    if rule_id:
        query = query.filter(SqlThrottleRun.rule_id == rule_id)
    if rule_name:
        query = query.join(SqlThrottleRule, SqlThrottleRule.id == SqlThrottleRun.rule_id).filter(
            SqlThrottleRule.rule_name.like(f'%{rule_name}%')
        )
    if status:
        query = query.filter(SqlThrottleRun.status == status)
    if is_hit is True:
        query = query.filter(SqlThrottleRun.hit_fingerprint_count > 0)
    elif is_hit is False:
        query = query.filter(SqlThrottleRun.hit_fingerprint_count == 0)

    total = query.count()
    rows = query.order_by(
        db.func.coalesce(SqlThrottleRun.sample_started_at, SqlThrottleRun.created_at).desc(),
        SqlThrottleRun.id.desc(),
    ).paginate(page=page, per_page=per_page, error_out=False)

    return success_response({
        'items': [row.to_dict() for row in rows.items],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@app.route('/api/sql-throttle-runs/<int:id>', methods=['GET'])
@admin_required
def get_sql_throttle_run(current_user, id):
    row = db.session.get(SqlThrottleRun, id)
    if not row:
        return error_response('运行记录不存在', 404)
    return success_response(row.to_dict())


@app.route('/api/sql-throttle-runs/<int:id>/kill-logs', methods=['GET'])
@admin_required
def get_sql_throttle_run_kill_logs(current_user, id):
    row = db.session.get(SqlThrottleRun, id)
    if not row:
        return error_response('运行记录不存在', 404)

    items = SqlThrottleKillLog.query.filter(
        SqlThrottleKillLog.run_id == id
    ).order_by(SqlThrottleKillLog.id.desc()).all()
    return success_response({'items': [item.to_dict() for item in items]})


@app.route('/api/sql-throttle-runs/<int:id>/snapshot', methods=['GET'])
@admin_required
def get_sql_throttle_run_snapshot(current_user, id):
    row = db.session.get(SqlThrottleRun, id)
    if not row:
        return error_response('运行记录不存在', 404)
    return success_response({'snapshot': row.snapshot()})


# ==================== 执行日志 API ====================

def _send_file_download(file_path, mimetype='text/plain'):
    filename = os.path.basename(file_path)
    response = send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _send_text_download(content, filename):
    buffer = io.BytesIO((content or '').encode('utf-8'))
    buffer.seek(0)
    response = send_file(
        buffer,
        mimetype='text/plain; charset=utf-8',
        as_attachment=True,
        download_name=filename,
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _read_log_file_text(file_path):
    with open(file_path, 'rb') as file_obj:
        raw = file_obj.read()

    for encoding in ('utf-8', 'utf-8-sig', 'gb18030', 'gbk'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw.decode('utf-8', errors='replace')


def _resolve_archive_log_content(log_id):
    log = ExecutionLog.query.get(log_id)
    if not log:
        return None, '执行日志不存在', 404

    log_file = log.log_file
    if not log_file or not os.path.exists(log_file):
        return {'content': '', 'has_file': False}, None, 200

    try:
        return {'content': _read_log_file_text(log_file), 'has_file': True}, None, 200
    except Exception as e:
        return None, f'读取日志失败: {str(e)}', 500


@app.route('/api/execution-logs', methods=['GET'])
@admin_required
def get_execution_logs(current_user):
    """获取执行日志列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    task_id = request.args.get('task_id', None, type=int)
    task_name = request.args.get('task_name', '')
    status = request.args.get('status', None)
    log_type = request.args.get('log_type')

    data = ExecutionLogService.get_log_list(
        page=page,
        per_page=per_page,
        task_name=task_name,
        status=status,
        log_type=log_type,
        task_id=task_id,
    )
    return success_response(data)


@app.route('/api/execution-logs/<int:id>', methods=['GET'])
@admin_required
def get_execution_log(current_user, id):
    """获取执行日志详情"""
    log = ExecutionLogService.get_log_detail(id)
    if not log:
        return error_response('日志不存在', 404)
    return success_response(log)


@app.route('/api/execution-logs/<int:id>/download', methods=['GET'])
@admin_required
def download_execution_log(current_user, id):
    """下载执行日志文件"""
    log = ExecutionLog.query.get(id)
    if not log or not log.log_file:
        return error_response('日志文件不存在', 404)

    try:
        import os
        if os.path.exists(log.log_file):
            return _send_file_download(log.log_file)
        else:
            return error_response('日志文件已被删除', 404)
    except Exception as e:
        return error_response(f'下载失败: {str(e)}', 500)


@app.route('/api/execution-logs/<string:log_type>/<int:id>/download', methods=['GET'])
@admin_required
def download_typed_execution_log(current_user, log_type, id):
    """下载统一执行日志文件"""
    if log_type == 'flashback':
        artifact_id = request.args.get('artifact_id')
        file_path, error, status_code = FlashbackService.resolve_download_file(id, artifact_id or None)
        if error:
            return error_response(error, status_code)
        if not file_path or not os.path.exists(file_path):
            return error_response('日志文件不存在', 404)
        return _send_file_download(file_path)

    if log_type == 'archive':
        return download_execution_log(current_user, id)

    if log_type == 'sql_throttle_run':
        content = ExecutionLogService.get_sql_throttle_run_log_content(id)
        if content is None:
            return error_response('日志不存在', 404)
        return _send_text_download(content, f'sql_throttle_run_{id}.log')

    if log_type == 'sql_kill':
        content = ExecutionLogService.get_sql_kill_log_content(id)
        if content is None:
            return error_response('日志不存在', 404)
        return _send_text_download(content, f'sql_kill_{id}.log')

    return error_response('日志类型不存在', 404)


@app.route('/api/execution-logs/<int:id>/log-content', methods=['GET'])
@admin_required
def get_log_content(current_user, id):
    """获取执行日志的实时内容"""
    data, error, status_code = _resolve_archive_log_content(id)
    if error:
        return error_response(error, status_code)
    return success_response(data)


@app.route('/api/execution-logs/<string:log_type>/<int:id>/log-content', methods=['GET'])
@admin_required
def get_typed_log_content(current_user, log_type, id):
    """获取统一执行日志内容"""
    if log_type == 'flashback':
        data, error, status_code = FlashbackService.get_log_content(id)
        if error:
            return error_response(error, status_code)
        return success_response(data)

    if log_type == 'archive':
        data, error, status_code = _resolve_archive_log_content(id)
        if error:
            return error_response(error, status_code)
        return success_response(data)

    if log_type == 'sql_throttle_run':
        content = ExecutionLogService.get_sql_throttle_run_log_content(id)
        if content is None:
            return error_response('日志不存在', 404)
        return success_response({'content': content, 'has_file': True})

    if log_type == 'sql_kill':
        content = ExecutionLogService.get_sql_kill_log_content(id)
        if content is None:
            return error_response('日志不存在', 404)
        return success_response({'content': content, 'has_file': True})

    return error_response('日志类型不存在', 404)


@app.route('/api/flashback-tasks/<int:id>/artifacts', methods=['GET'])
@admin_required
def list_flashback_artifacts(current_user, id):
    """获取闪回任务产物列表"""
    task = FlashbackService.get_task_detail(id)
    if not task:
        return error_response('闪回任务不存在', 404)
    return success_response({'items': task.get('artifacts', [])})


@app.route('/api/flashback-tasks/<int:id>/artifacts/<string:artifact_id>/download', methods=['GET'])
@admin_required
def download_flashback_artifact(current_user, id, artifact_id):
    """下载闪回任务产物文件"""
    file_path, error, status_code = FlashbackService.resolve_download_file(id, artifact_id)
    if error:
        return error_response(error, status_code)
    if not file_path or not os.path.exists(file_path):
        return error_response('文件不存在', 404)
    return _send_file_download(file_path)


@app.route('/api/health', methods=['GET'])
def health_check():
    return success_response({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
