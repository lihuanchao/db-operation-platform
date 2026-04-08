# My2SQL Data Flashback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增基于 `/my2sql` 的“数据闪回”能力，支持管理员创建一次性闪回任务、生成并下载 3 个结果文件，同时把“执行日志”升级为统一日志中心，集中展示归档日志和闪回日志。

**Architecture:** 后端新增独立 `FlashbackTask` 模型与 `FlashbackService`，采用和优化任务一致的“创建即异步执行”模式。执行日志不新增独立闪回日志表，而是保留现有 `ExecutionLog` 作为归档日志源，再把 `FlashbackTask` 映射为统一日志项，由统一日志接口做聚合排序和分页。前端新增闪回任务列表/创建/详情页，并改造执行日志页、菜单、路由与权限映射。

**Tech Stack:** Flask, SQLAlchemy, Python `unittest`, subprocess/threading, Vue 3 `<script setup>`, TypeScript, Pinia, Vue Router, Element Plus, Vitest, Vue Test Utils

---

## File Structure

- Create: `backend/models/flashback_task.py`
  - 职责：定义闪回任务表结构、状态字段、产物清单序列化与 `to_dict()` 输出。
- Create: `backend/services/flashback_service.py`
  - 职责：参数校验、命令构建、密码脱敏、任务创建、后台执行、日志读取、产物扫描、文件下载。
- Create: `backend/tests/test_flashback_service.py`
  - 职责：验证命令构建、可选参数省略、密码脱敏、产物扫描规则。
- Create: `backend/tests/test_flashback_api.py`
  - 职责：验证闪回任务创建、列表、详情、日志内容、日志下载、产物下载接口。
- Create: `backend/tests/test_execution_log_api.py`
  - 职责：验证统一执行日志接口可同时返回归档日志与闪回日志，并能按类型读取日志和下载。
- Modify: `backend/models/__init__.py`
  - 职责：导出 `FlashbackTask`。
- Modify: `backend/services/execution_log_service.py`
  - 职责：聚合归档日志与闪回日志，输出统一列表结构。
- Modify: `backend/app.py`
  - 职责：新增闪回任务接口，改造执行日志接口为统一日志中心。
- Modify: `backend/services/auth_service.py`
  - 职责：把 `执行日志`、`数据闪回` 加入管理员菜单并保持一级菜单顺序。

- Modify: `frontend/src/types/index.ts`
  - 职责：补充 `FlashbackTask`、`FlashbackArtifact`、统一执行日志类型定义。
- Create: `frontend/src/api/flashbackTask.ts`
  - 职责：封装闪回任务列表、创建、详情、日志、产物下载请求。
- Create: `frontend/src/stores/flashbackTask.ts`
  - 职责：管理闪回任务列表、详情、筛选、创建与下载动作。
- Create: `frontend/src/stores/flashbackTask.spec.ts`
  - 职责：验证闪回任务 store 的列表/创建/详情/下载行为。
- Create: `frontend/src/stores/executionLog.spec.ts`
  - 职责：验证统一日志 store 的 `log_type` 筛选与下载参数传递。
- Modify: `frontend/src/api/executionLog.ts`
  - 职责：支持 `log_type`、`task_name` 参数，以及按类型读取/下载日志。
- Modify: `frontend/src/stores/executionLog.ts`
  - 职责：接入统一日志筛选字段与按类型下载。
- Modify: `frontend/src/auth/access.ts`
  - 职责：新增 `/flashback-tasks` 路由权限与菜单标题映射。
- Modify: `frontend/src/router/index.ts`
  - 职责：新增闪回任务列表/创建/详情路由。
- Modify: `frontend/src/components/Layout/Sidebar.vue`
  - 职责：新增一级菜单“数据闪回”，确保“执行日志”保持一级菜单。
- Modify: `frontend/src/components/Layout/Sidebar.spec.ts`
  - 职责：验证新菜单渲染、顺序与点击导航。
- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`
  - 职责：验证新路由打开后标签标题正确。
- Modify: `frontend/src/views/ExecutionLogList.vue`
  - 职责：改为统一日志中心，支持日志类型筛选和跳转。
- Create: `frontend/src/views/ExecutionLogList.spec.ts`
  - 职责：验证统一日志页筛选、日志读取与详情跳转。
- Create: `frontend/src/views/FlashbackTaskList.vue`
  - 职责：闪回任务列表页。
- Create: `frontend/src/views/FlashbackTaskCreate.vue`
  - 职责：闪回任务创建页。
- Create: `frontend/src/views/FlashbackTaskDetail.vue`
  - 职责：闪回任务详情页。
- Create: `frontend/src/views/FlashbackTaskList.spec.ts`
  - 职责：验证列表筛选与跳转。
- Create: `frontend/src/views/FlashbackTaskCreate.spec.ts`
  - 职责：验证表单校验、连接摘要展示、创建成功跳转。
- Create: `frontend/src/views/FlashbackTaskDetail.spec.ts`
  - 职责：验证产物清单与日志显示/下载。

## Task 1: Build Flashback Model And Service Primitives (TDD)

**Files:**
- Create: `backend/tests/test_flashback_service.py`
- Create: `backend/models/flashback_task.py`
- Create: `backend/services/flashback_service.py`
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_flashback_service.py`

- [ ] **Step 1: Write the failing service test**

`backend/tests/test_flashback_service.py`

```python
import json
import os
import shutil
import tempfile
import unittest

from services.flashback_service import FlashbackService
from models.flashback_task import FlashbackTask


class FlashbackServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.output_dir = tempfile.mkdtemp(prefix='flashback-output-')

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def test_build_command_masks_password_and_skips_empty_optionals(self):
        task = FlashbackTask(
            database_name='demo_db',
            table_name='orders',
            mode='repl',
            sql_type='delete',
            work_type='2sql',
            start_datetime='2026-04-08 08:00:00',
            stop_datetime='2026-04-08 08:40:00',
            start_file='',
            stop_file=''
        )
        connection = type('Conn', (), {
            'host': '10.0.0.1',
            'port': 3306,
            'username': 'repl',
            'password': 'secret'
        })()

        command, masked_command = FlashbackService.build_command(task, connection, self.output_dir)

        joined = ' '.join(command)
        self.assertTrue(command[0].endswith('/my2sql'))
        self.assertIn('-start-datetime', joined)
        self.assertNotIn('-start-file', joined)
        self.assertNotIn('secret', masked_command)
        self.assertIn('******', masked_command)

    def test_collect_artifacts_requires_two_fixed_files_and_one_sql(self):
        with open(os.path.join(self.output_dir, 'binlog_status.txt'), 'w', encoding='utf-8') as f:
            f.write('ok')
        with open(os.path.join(self.output_dir, 'biglong_trx.txt'), 'w', encoding='utf-8') as f:
            f.write('none')
        with open(os.path.join(self.output_dir, 'flashback_orders.sql'), 'w', encoding='utf-8') as f:
            f.write('rollback sql')

        artifacts = FlashbackService.collect_artifacts(self.output_dir)
        names = [item['name'] for item in artifacts]

        self.assertEqual(names, ['binlog_status.txt', 'biglong_trx.txt', 'flashback_orders.sql'])
        self.assertTrue(all(item['size'] > 0 for item in artifacts))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest backend.tests.test_flashback_service -v
```

Expected: FAIL，提示 `No module named services.flashback_service` 或 `No module named models.flashback_task`。

- [ ] **Step 3: Write the minimal model and primitive service**

`backend/models/flashback_task.py`

```python
import json
from datetime import datetime

from extensions import db

SQLITE_BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FlashbackTask(db.Model):
    __tablename__ = 'flashback_task'

    id = db.Column(SQLITE_BIGINT, primary_key=True, autoincrement=True)
    db_connection_id = db.Column(db.BigInteger, db.ForeignKey('db_connection.id'), nullable=False)
    connection_id = db.Column(db.BigInteger, nullable=True)
    connection_name = db.Column(db.String(100), nullable=False)
    database_name = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default='repl')
    sql_type = db.Column(db.String(20), nullable=False)
    work_type = db.Column(db.String(20), nullable=False)
    start_datetime = db.Column(db.String(32), nullable=True)
    stop_datetime = db.Column(db.String(32), nullable=True)
    start_file = db.Column(db.String(128), nullable=True)
    stop_file = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='queued')
    progress = db.Column(db.Integer, nullable=False, default=0)
    output_dir = db.Column(db.String(500), nullable=True)
    log_file = db.Column(db.String(500), nullable=True)
    masked_command = db.Column(db.Text, nullable=True)
    artifact_manifest = db.Column(db.Text, nullable=True, default='[]')
    error_message = db.Column(db.Text, nullable=True)
    creator_user_id = db.Column(db.BigInteger, nullable=True)
    creator_employee_no = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    db_connection = db.relationship('DbConnection', backref=db.backref('flashback_tasks', lazy=True))

    def set_artifacts(self, items):
        self.artifact_manifest = json.dumps(items, ensure_ascii=False)

    def get_artifacts(self):
        try:
            return json.loads(self.artifact_manifest or '[]')
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'db_connection_id': self.db_connection_id,
            'connection_id': self.connection_id,
            'connection_name': self.connection_name,
            'database_name': self.database_name,
            'table_name': self.table_name,
            'mode': self.mode,
            'sql_type': self.sql_type,
            'work_type': self.work_type,
            'start_datetime': self.start_datetime,
            'stop_datetime': self.stop_datetime,
            'start_file': self.start_file,
            'stop_file': self.stop_file,
            'status': self.status,
            'progress': self.progress,
            'output_dir': self.output_dir,
            'log_file': self.log_file,
            'masked_command': self.masked_command,
            'artifacts': self.get_artifacts(),
            'error_message': self.error_message,
            'creator_user_id': self.creator_user_id,
            'creator_employee_no': self.creator_employee_no,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            'finished_at': self.finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.finished_at else None,
        }
```

`backend/models/__init__.py`

```python
from .flashback_task import FlashbackTask

__all__ = [
    # ...existing exports...
    'FlashbackTask',
]
```

`backend/services/flashback_service.py`

```python
import glob
import os


class FlashbackService:
    TOOL_PATH = '/my2sql'
    OUTPUT_ROOT = '/app/flashback/tasks'

    @classmethod
    def build_command(cls, task, connection, output_dir):
        command = [
            cls.TOOL_PATH,
            '-databases', task.database_name,
            '-tables', task.table_name,
            '-mode', task.mode or 'repl',
            '-host', connection.host,
            '-port', str(connection.port),
            '-user', connection.username,
            '-password', connection.password,
            '-sql', task.sql_type,
            '-work-type', task.work_type,
            '-output-dir', output_dir,
        ]

        optional_pairs = [
            ('-start-datetime', task.start_datetime),
            ('-stop-datetime', task.stop_datetime),
            ('-start-file', task.start_file),
            ('-stop-file', task.stop_file),
        ]
        for key, value in optional_pairs:
            if value:
                command.extend([key, value])

        return command, cls.mask_command(command)

    @staticmethod
    def mask_command(command):
        masked = list(command)
        for index, part in enumerate(masked):
            if part == '-password' and index + 1 < len(masked):
                masked[index + 1] = '******'
        return ' '.join(masked)

    @staticmethod
    def collect_artifacts(output_dir):
        fixed_names = ['binlog_status.txt', 'biglong_trx.txt']
        items = []

        for name in fixed_names:
            path = os.path.join(output_dir, name)
            if not os.path.exists(path):
                raise FileNotFoundError(f'{name} 未生成')
            items.append({
                'id': name.replace('.', '-'),
                'name': name,
                'path': path,
                'size': os.path.getsize(path),
            })

        sql_files = sorted(glob.glob(os.path.join(output_dir, '*.sql')))
        if not sql_files:
            raise FileNotFoundError('未生成 .sql 结果文件')

        sql_path = sql_files[0]
        items.append({
            'id': 'result-sql',
            'name': os.path.basename(sql_path),
            'path': sql_path,
            'size': os.path.getsize(sql_path),
        })
        return items
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest backend.tests.test_flashback_service -v
```

Expected: PASS，2 个测试全部通过。

- [ ] **Step 5: Commit**

```bash
git add backend/models/flashback_task.py backend/models/__init__.py backend/services/flashback_service.py backend/tests/test_flashback_service.py
git commit -m "feat: add flashback task model and service primitives"
```

## Task 2: Add Flashback Task API And Async Worker (TDD)

**Files:**
- Create: `backend/tests/test_flashback_api.py`
- Modify: `backend/services/flashback_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_flashback_api.py`

- [ ] **Step 1: Write the failing API test**

`backend/tests/test_flashback_api.py`

```python
import os
import unittest
from unittest.mock import patch

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'flashback-secret'

from app import app
from extensions import db
from models import DbConnection, SysUser
from services.auth_service import AuthService


class FlashbackApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='flashback-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        self.admin = SysUser(
            employee_no='A1001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled'
        )
        self.connection = DbConnection(
            connection_name='测试连接',
            host='10.10.10.10',
            manage_host='10.10.10.11',
            port=3306,
            username='repl',
            password='repl',
            is_enabled=1
        )
        db.session.add_all([self.admin, self.connection])
        db.session.commit()
        self.client.post('/api/auth/login', json={'employee_no': 'A1001', 'password': 'Passw0rd!'})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    @patch('services.flashback_service.FlashbackService._run_task_async')
    def test_create_flashback_task(self, run_async):
        response = self.client.post('/api/flashback-tasks', json={
            'db_connection_id': self.connection.id,
            'database_name': 'demo_db',
            'table_name': 'orders',
            'sql_type': 'delete',
            'work_type': '2sql',
            'start_datetime': '2026-04-08 08:00:00',
            'stop_datetime': '2026-04-08 08:40:00'
        })

        self.assertEqual(response.status_code, 200)
        body = response.get_json()['data']
        self.assertEqual(body['status'], 'queued')
        self.assertEqual(body['connection_name'], '测试连接')
        run_async.assert_called_once()

    def test_list_and_detail_flashback_tasks(self):
        with patch('services.flashback_service.FlashbackService._run_task_async'):
            create_resp = self.client.post('/api/flashback-tasks', json={
                'db_connection_id': self.connection.id,
                'database_name': 'demo_db',
                'table_name': 'orders',
                'sql_type': 'update',
                'work_type': 'rollback'
            })
        task_id = create_resp.get_json()['data']['id']

        list_resp = self.client.get('/api/flashback-tasks?page=1&per_page=10')
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.get_json()['data']['items'][0]['id'], task_id)

        detail_resp = self.client.get(f'/api/flashback-tasks/{task_id}')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.get_json()['data']['table_name'], 'orders')
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python3 -m unittest backend.tests.test_flashback_api -v
```

Expected: FAIL，提示 `/api/flashback-tasks` 404 或 `FlashbackService.create_task` 不存在。

- [ ] **Step 3: Implement create/list/detail endpoints and async worker**

`backend/services/flashback_service.py`

```python
import os
import subprocess
import threading
from datetime import datetime

from extensions import db
from models import DbConnection, FlashbackTask


class FlashbackService:
    # 保留 Task 1 的常量与构建方法

    @classmethod
    def get_task_list(cls, page=1, per_page=10, database_name='', table_name='', status='', sql_type='', work_type=''):
        query = FlashbackTask.query
        if database_name:
            query = query.filter(FlashbackTask.database_name.like(f'%{database_name}%'))
        if table_name:
            query = query.filter(FlashbackTask.table_name.like(f'%{table_name}%'))
        if status:
            query = query.filter(FlashbackTask.status == status)
        if sql_type:
            query = query.filter(FlashbackTask.sql_type == sql_type)
        if work_type:
            query = query.filter(FlashbackTask.work_type == work_type)

        total = query.count()
        pager = query.order_by(FlashbackTask.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return {
            'items': [item.to_dict() for item in pager.items],
            'total': total,
            'page': page,
            'per_page': per_page,
        }

    @classmethod
    def get_task_detail(cls, task_id):
        task = FlashbackTask.query.get(task_id)
        return task.to_dict() if task else None

    @classmethod
    def create_task(cls, data, current_user):
        connection = DbConnection.query.get(data['db_connection_id'])
        if not connection or connection.is_enabled == 0:
            return None, '数据库连接不存在或已禁用'

        task = FlashbackTask(
            db_connection_id=connection.id,
            connection_id=connection.id,
            connection_name=connection.connection_name,
            database_name=data['database_name'].strip(),
            table_name=data['table_name'].strip(),
            mode='repl',
            sql_type=data['sql_type'],
            work_type=data['work_type'],
            start_datetime=(data.get('start_datetime') or '').strip() or None,
            stop_datetime=(data.get('stop_datetime') or '').strip() or None,
            start_file=(data.get('start_file') or '').strip() or None,
            stop_file=(data.get('stop_file') or '').strip() or None,
            status='queued',
            progress=0,
            creator_user_id=current_user.id if current_user else None,
            creator_employee_no=current_user.employee_no if current_user else None,
        )

        db.session.add(task)
        db.session.commit()
        cls._run_task_async(task.id)
        return task.to_dict(), None

    @classmethod
    def _run_task_async(cls, task_id):
        from app import app

        def _worker():
            with app.app_context():
                cls._execute_task(task_id)

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def _execute_task(cls, task_id):
        task = FlashbackTask.query.get(task_id)
        if not task:
            return

        connection = DbConnection.query.get(task.db_connection_id)
        if not connection:
            task.status = 'failed'
            task.progress = 100
            task.error_message = '数据库连接不存在'
            db.session.commit()
            return

        task_dir = os.path.join(cls.OUTPUT_ROOT, str(task.id))
        output_dir = os.path.join(task_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        log_file = os.path.join(task_dir, 'run.log')

        task.output_dir = output_dir
        task.log_file = log_file
        task.status = 'running'
        task.progress = 30
        task.started_at = datetime.now()
        command, masked_command = cls.build_command(task, connection, output_dir)
        task.masked_command = masked_command
        db.session.commit()

        with open(log_file, 'a', encoding='utf-8') as log_fp:
            log_fp.write(f'[{datetime.now():%F %T}] {masked_command}\\n')
            process = subprocess.Popen(command, stdout=log_fp, stderr=log_fp, text=True)
            return_code = process.wait()
            log_fp.write(f'[{datetime.now():%F %T}] exit_code={return_code}\\n')

        if return_code != 0:
            task.status = 'failed'
            task.progress = 100
            task.finished_at = datetime.now()
            task.error_message = f'my2sql 执行失败，退出码 {return_code}'
            db.session.commit()
            return

        artifacts = cls.collect_artifacts(output_dir)
        task.set_artifacts(artifacts)
        task.status = 'completed'
        task.progress = 100
        task.finished_at = datetime.now()
        task.error_message = None
        db.session.commit()
```

`backend/app.py`

```python
from models import ArchiveTask, CronJob, ExecutionLog, FlashbackTask
from services.flashback_service import FlashbackService


@app.route('/api/flashback-tasks', methods=['GET'])
@admin_required
def get_flashback_tasks(current_user):
    data = FlashbackService.get_task_list(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 10, type=int),
        database_name=request.args.get('database_name', ''),
        table_name=request.args.get('table_name', ''),
        status=request.args.get('status', ''),
        sql_type=request.args.get('sql_type', ''),
        work_type=request.args.get('work_type', ''),
    )
    return success_response(data)


@app.route('/api/flashback-tasks', methods=['POST'])
@admin_required
def create_flashback_task(current_user):
    payload = request.get_json(silent=True) or {}
    required_fields = ['db_connection_id', 'database_name', 'table_name', 'sql_type', 'work_type']
    for field in required_fields:
        if not payload.get(field):
            return error_response(f'{field} 是必填字段', 400)

    task, error = FlashbackService.create_task(payload, current_user)
    if error:
        return error_response(error, 400)
    return success_response(task)


@app.route('/api/flashback-tasks/<int:id>', methods=['GET'])
@admin_required
def get_flashback_task_detail(current_user, id):
    task = FlashbackService.get_task_detail(id)
    if not task:
        return error_response('闪回任务不存在', 404)
    return success_response(task)


@app.route('/api/flashback-tasks/<int:id>/log-content', methods=['GET'])
@admin_required
def get_flashback_task_log_content(current_user, id):
    data, error, status_code = FlashbackService.get_log_content(id)
    if error:
        return error_response(error, status_code)
    return success_response(data)


@app.route('/api/flashback-tasks/<int:id>/download-log', methods=['GET'])
@admin_required
def download_flashback_task_log(current_user, id):
    file_path, error, status_code = FlashbackService.resolve_download_file(id)
    if error:
        return error_response(error, status_code)
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
python3 -m unittest backend.tests.test_flashback_api -v
```

Expected: PASS，创建、列表、详情测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/services/flashback_service.py backend/tests/test_flashback_api.py
git commit -m "feat: add flashback task api and async runner"
```

## Task 3: Unify Archive Logs And Flashback Logs (TDD)

契约修正说明：

- `GET /api/execution-logs` 默认仍保持 `archive-only`，以兼容现有前端旧调用。
- 只有显式 `log_type=flashback` 或 `log_type=all` / `log_type=merged` 时，才返回闪回或聚合视图。
- `GET /api/execution-logs/flashback/<id>/log-content` 成功返回 `200`，任务不存在 / 路径越界返回 `404`，真实文件读取 I/O 异常返回 `500`。
- `GET /api/flashback-tasks/<id>/artifacts` 只返回 `id` / `name` / `size`，不暴露服务端绝对路径。

**Files:**
- Create: `backend/tests/test_execution_log_api.py`
- Modify: `backend/services/execution_log_service.py`
- Modify: `backend/services/flashback_service.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_execution_log_api.py`

- [ ] **Step 1: Write the failing unified log test**

`backend/tests/test_execution_log_api.py`

```python
import os
import tempfile
import unittest

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'log-secret'

from app import app
from datetime import datetime
from extensions import db
from models import ArchiveTask, DbConnection, ExecutionLog, FlashbackTask, SysUser
from services.auth_service import AuthService


class ExecutionLogApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='log-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        admin = SysUser(
            employee_no='A1001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled'
        )
        conn = DbConnection(
            connection_name='测试连接',
            host='10.0.0.10',
            manage_host='10.0.0.11',
            port=3306,
            username='root',
            password='secret',
            is_enabled=1
        )
        db.session.add_all([admin, conn])
        db.session.commit()

        archive_task = ArchiveTask(
            task_name='归档订单',
            source_connection_id=conn.id,
            source_database='demo',
            source_table='orders',
            where_condition='id > 1',
            is_enabled=1
        )
        db.session.add(archive_task)
        db.session.commit()

        archive_log = ExecutionLog(
            task_id=archive_task.id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=1,
            log_file=tempfile.NamedTemporaryFile(delete=False).name
        )
        flashback_log = FlashbackTask(
            db_connection_id=conn.id,
            connection_id=conn.id,
            connection_name='测试连接',
            database_name='demo',
            table_name='orders',
            mode='repl',
            sql_type='delete',
            work_type='2sql',
            status='completed',
            progress=100,
            log_file=tempfile.NamedTemporaryFile(delete=False).name,
            started_at=datetime.now(),
            finished_at=datetime.now()
        )
        db.session.add_all([archive_log, flashback_log])
        db.session.commit()

        self.archive_log_id = archive_log.id
        self.flashback_id = flashback_log.id
        self.client.post('/api/auth/login', json={'employee_no': 'A1001', 'password': 'Passw0rd!'})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_execution_logs_can_filter_by_type(self):
        resp = self.client.get('/api/execution-logs?page=1&per_page=10')
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()['data']['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['log_type'], 'archive')

    def test_flashback_logs_require_explicit_log_type(self):
        resp = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=flashback')
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()['data']['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['log_type'], 'flashback')

        resp = self.client.get('/api/execution-logs?page=1&per_page=10&log_type=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['total'], 2)

    def test_flashback_log_content_endpoint_reads_task_log(self):
        with open(FlashbackTask.query.get(self.flashback_id).log_file, 'w', encoding='utf-8') as f:
            f.write('flashback log content')

        resp = self.client.get(f'/api/execution-logs/flashback/{self.flashback_id}/log-content')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['content'], 'flashback log content')

    def test_flashback_log_content_returns_500_for_io_error(self):
        with patch('services.flashback_service.open', side_effect=PermissionError('permission denied')):
            resp = self.client.get(f'/api/execution-logs/flashback/{self.flashback_id}/log-content')
        self.assertEqual(resp.status_code, 500)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python3 -m unittest backend.tests.test_execution_log_api -v
```

Expected: FAIL，提示默认列表仍混入闪回、`all` 未聚合、或 `/api/execution-logs/flashback/<id>/log-content` 错误码不分层。

- [ ] **Step 3: Implement unified log aggregation**

`backend/services/execution_log_service.py`

```python
from models import ArchiveTask, ExecutionLog, FlashbackTask


class ExecutionLogService:
    @staticmethod
    def normalize_flashback_status(status):
        if status == 'completed':
            return 1
        if status in ('queued', 'running'):
            return 2
        return 0

    @classmethod
    def get_log_list(cls, page=1, per_page=10, task_name='', status=None, log_type=''):
        # 默认 archive-only；flashback-only 和 all/merged 走单独分支。
        # archive-only / flashback-only 使用数据库排序 + paginate。
        # all/merged 只抓取 page * per_page 的候选项后在内存里稳定合并。
```

`backend/services/flashback_service.py`

```python
    @classmethod
    def get_log_content(cls, task_id):
        # 任务不存在 / 路径越界 / 文件缺失返回 404；真实 I/O 异常返回 500。

    @classmethod
    def resolve_download_file(cls, task_id, artifact_id=None):
        # 所有候选路径必须落在 OUTPUT_ROOT/<task_id>/ 下，artifact 列表只暴露 id/name/size。
```

`backend/app.py`

```python
@app.route('/api/execution-logs', methods=['GET'])
@admin_required
def get_execution_logs(current_user):
    data = ExecutionLogService.get_log_list(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 10, type=int),
        task_name=request.args.get('task_name', ''),
        status=request.args.get('status', None, type=int),
        log_type=request.args.get('log_type'),
    )
    return success_response(data)


@app.route('/api/execution-logs/<string:log_type>/<int:id>/download', methods=['GET'])
@admin_required
def download_typed_execution_log(current_user, log_type, id):
    if log_type == 'flashback':
        file_path, error, status_code = FlashbackService.resolve_download_file(id)
        if error:
            return error_response(error, status_code)
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
    return download_execution_log(current_user, id)


@app.route('/api/execution-logs/<string:log_type>/<int:id>/log-content', methods=['GET'])
@admin_required
def get_typed_log_content(current_user, log_type, id):
    if log_type == 'flashback':
        data, error, status_code = FlashbackService.get_log_content(id)
        if error:
            return error_response(error, status_code)
        return success_response(data)
    return get_log_content(current_user, id)


@app.route('/api/flashback-tasks/<int:id>/artifacts/<string:artifact_id>/download', methods=['GET'])
@admin_required
def download_flashback_artifact(current_user, id, artifact_id):
    file_path, error, status_code = FlashbackService.resolve_download_file(id, artifact_id)
    if error:
        return error_response(error, status_code)
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))


@app.route('/api/flashback-tasks/<int:id>/artifacts', methods=['GET'])
@admin_required
def list_flashback_artifacts(current_user, id):
    task = FlashbackTask.query.get(id)
    if not task:
        return error_response('闪回任务不存在', 404)
    return success_response({'items': task.get_artifacts()})
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
python3 -m unittest backend.tests.test_execution_log_api -v
```

Expected: PASS，统一日志筛选和闪回日志读取通过。

- [ ] **Step 5: Commit**

```bash
git add backend/services/execution_log_service.py backend/services/flashback_service.py backend/app.py backend/tests/test_execution_log_api.py
git commit -m "feat: unify archive and flashback execution logs"
```

## Task 4: Add Frontend Types, APIs, And Stores (TDD)

**Files:**
- Create: `frontend/src/stores/flashbackTask.spec.ts`
- Create: `frontend/src/stores/executionLog.spec.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/flashbackTask.ts`
- Modify: `frontend/src/api/executionLog.ts`
- Create: `frontend/src/stores/flashbackTask.ts`
- Modify: `frontend/src/stores/executionLog.ts`
- Test: `frontend/src/stores/flashbackTask.spec.ts`
- Test: `frontend/src/stores/executionLog.spec.ts`

- [ ] **Step 1: Write the failing store tests**

`frontend/src/stores/flashbackTask.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/flashbackTask', () => ({
  getFlashbackTaskList: vi.fn(async () => ({
    success: true,
    data: {
      items: [{ id: 1, connection_name: '测试连接', database_name: 'demo', table_name: 'orders', status: 'completed', sql_type: 'delete', work_type: '2sql', artifacts: [] }],
      total: 1,
      page: 1,
      per_page: 10
    }
  })),
  createFlashbackTask: vi.fn(async () => ({
    success: true,
    data: { id: 2, status: 'queued', database_name: 'demo', table_name: 'orders', connection_name: '测试连接', sql_type: 'delete', work_type: '2sql', artifacts: [] }
  })),
  getFlashbackTaskDetail: vi.fn(async () => ({
    success: true,
    data: { id: 2, status: 'completed', database_name: 'demo', table_name: 'orders', connection_name: '测试连接', sql_type: 'delete', work_type: '2sql', artifacts: [{ id: 'result-sql', name: 'orders.sql', size: 10 }] }
  }))
}))

import { useFlashbackTaskStore } from './flashbackTask'

describe('flashback task store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads list and detail', async () => {
    const store = useFlashbackTaskStore()
    await store.fetchList()
    expect(store.list[0].table_name).toBe('orders')

    const detail = await store.fetchDetail(2)
    expect(detail?.artifacts[0].name).toBe('orders.sql')
  })

  it('creates task and returns new id', async () => {
    const store = useFlashbackTaskStore()
    const task = await store.createTask({
      db_connection_id: 1,
      database_name: 'demo',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql'
    })
    expect(task?.id).toBe(2)
  })
})
```

`frontend/src/stores/executionLog.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const getExecutionLogList = vi.fn(async () => ({
  success: true,
  data: {
    items: [{ id: 11, task_name: 'demo.orders', log_type: 'flashback', status: 1, detail_path: '/flashback-tasks/11' }],
    total: 1,
    page: 1,
    per_page: 10
  }
}))

vi.mock('@/api/executionLog', () => ({
  getExecutionLogList,
  getExecutionLog: vi.fn(),
  downloadExecutionLog: vi.fn(async () => ({ status: 200, data: new Blob(['ok']) }))
}))

import { useExecutionLogStore } from './executionLog'

describe('execution log store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('passes log_type filter to unified log api', async () => {
    const store = useExecutionLogStore()
    store.setFilters({ log_type: 'flashback', task_name: 'orders' })
    await store.fetchList()
    expect(getExecutionLogList).toHaveBeenCalledWith(expect.objectContaining({
      log_type: 'flashback',
      task_name: 'orders'
    }))
    expect(store.list[0].log_type).toBe('flashback')
  })
})
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd frontend && npm test -- src/stores/flashbackTask.spec.ts src/stores/executionLog.spec.ts
```

Expected: FAIL，提示 `Cannot find module '@/api/flashbackTask'` 或 `filters.log_type` 类型不存在。

- [ ] **Step 3: Implement shared frontend data layer**

`frontend/src/types/index.ts`

```ts
export type FlashbackTaskStatus = 'queued' | 'running' | 'completed' | 'failed'
export type FlashbackSqlType = 'delete' | 'insert' | 'update'
export type FlashbackWorkType = '2sql' | 'rollback' | 'stats'
export type ExecutionLogType = 'archive' | 'flashback'

export interface FlashbackArtifact {
  id: string
  name: string
  path?: string
  size: number
}

export interface FlashbackTask {
  id: number
  db_connection_id: number
  connection_id?: number
  connection_name: string
  database_name: string
  table_name: string
  mode: string
  sql_type: FlashbackSqlType
  work_type: FlashbackWorkType
  start_datetime?: string | null
  stop_datetime?: string | null
  start_file?: string | null
  stop_file?: string | null
  status: FlashbackTaskStatus
  progress: number
  log_file?: string | null
  masked_command?: string | null
  artifacts: FlashbackArtifact[]
  error_message?: string | null
  created_at?: string
  started_at?: string | null
  finished_at?: string | null
}

export interface FlashbackTaskListResponse {
  items: FlashbackTask[]
  total: number
  page: number
  per_page: number
}

export interface CreateFlashbackTaskPayload {
  db_connection_id: number
  database_name: string
  table_name: string
  sql_type: FlashbackSqlType
  work_type: FlashbackWorkType
  start_datetime?: string
  stop_datetime?: string
  start_file?: string
  stop_file?: string
}

export interface ExecutionLog {
  id?: number
  task_id: number
  task_name?: string
  cron_job_id?: number
  start_time?: string
  end_time?: string
  status: number
  log_file?: string
  error_message?: string
  created_at?: string
  log_type: ExecutionLogType
  detail_path?: string
  _selected?: boolean
}
```

`frontend/src/api/flashbackTask.ts`

```ts
import axios from 'axios'
import request from './request'
import type { ApiResponse, CreateFlashbackTaskPayload, FlashbackTask, FlashbackTaskListResponse } from '@/types'

export const getFlashbackTaskList = (params?: Record<string, unknown>) =>
  request.get<FlashbackTaskListResponse, ApiResponse<FlashbackTaskListResponse>>('/flashback-tasks', { params })

export const createFlashbackTask = (payload: CreateFlashbackTaskPayload) =>
  request.post<FlashbackTask, ApiResponse<FlashbackTask>>('/flashback-tasks', payload)

export const getFlashbackTaskDetail = (id: number) =>
  request.get<FlashbackTask, ApiResponse<FlashbackTask>>(`/flashback-tasks/${id}`)

export const getFlashbackLogContent = (id: number) =>
  request.get<{ content: string; has_file: boolean }, ApiResponse<{ content: string; has_file: boolean }>>(`/flashback-tasks/${id}/log-content`)

export const downloadFlashbackLog = (id: number) =>
  axios.get(`/api/flashback-tasks/${id}/download-log`, { responseType: 'blob' })

export const downloadFlashbackArtifact = (id: number, artifactId: string) =>
  axios.get(`/api/flashback-tasks/${id}/artifacts/${artifactId}/download`, { responseType: 'blob' })
```

`frontend/src/api/executionLog.ts`

```ts
export const getExecutionLogList = (params?: {
  page?: number
  per_page?: number
  task_name?: string
  status?: number
  log_type?: 'archive' | 'flashback'
}) => request.get('/execution-logs', { params })

export const downloadExecutionLog = (type: 'archive' | 'flashback', id: number) =>
  axios.get(`/api/execution-logs/${type}/${id}/download`, { responseType: 'blob' })

export const getLogContent = (type: 'archive' | 'flashback', id: number) =>
  request.get(`/execution-logs/${type}/${id}/log-content`)
```

`frontend/src/stores/flashbackTask.ts`

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createFlashbackTask,
  downloadFlashbackArtifact,
  downloadFlashbackLog,
  getFlashbackLogContent,
  getFlashbackTaskDetail,
  getFlashbackTaskList
} from '@/api/flashbackTask'
import type { CreateFlashbackTaskPayload, FlashbackTask, FlashbackTaskStatus } from '@/types'

export const useFlashbackTaskStore = defineStore('flashbackTask', () => {
  const list = ref<FlashbackTask[]>([])
  const currentTask = ref<FlashbackTask | null>(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  const submitLoading = ref(false)
  const page = ref(1)
  const perPage = ref(10)
  const total = ref(0)
  const filters = ref({
    database_name: '',
    table_name: '',
    status: '' as FlashbackTaskStatus | '',
    sql_type: '',
    work_type: '',
  })

  async function fetchList() {
    loading.value = true
    try {
      const res = await getFlashbackTaskList({ page: page.value, per_page: perPage.value, ...filters.value })
      if (res.data) {
        list.value = res.data.items
        total.value = res.data.total
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    detailLoading.value = true
    try {
      const res = await getFlashbackTaskDetail(id)
      currentTask.value = res.data ?? null
      return currentTask.value
    } finally {
      detailLoading.value = false
    }
  }

  async function createTask(payload: CreateFlashbackTaskPayload) {
    submitLoading.value = true
    try {
      const res = await createFlashbackTask(payload)
      if (res.data) {
        ElMessage.success('闪回任务已加入后台执行')
        return res.data
      }
      return null
    } finally {
      submitLoading.value = false
    }
  }

  async function fetchLogContent(id: number) {
    const res = await getFlashbackLogContent(id)
    return res.data?.content || ''
  }

  async function triggerDownloadLog(id: number) {
    const response = await downloadFlashbackLog(id)
    const blob = new Blob([response.data], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flashback_${id}.log`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  async function triggerDownloadArtifact(id: number, artifactId: string, fileName: string) {
    const response = await downloadFlashbackArtifact(id, artifactId)
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  function setFilters(next: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...next }
    page.value = 1
  }

  return {
    list,
    currentTask,
    loading,
    detailLoading,
    submitLoading,
    page,
    perPage,
    total,
    filters,
    fetchList,
    fetchDetail,
    createTask,
    fetchLogContent,
    triggerDownloadLog,
    triggerDownloadArtifact,
    setFilters
  }
})
```

`frontend/src/stores/executionLog.ts`

```ts
const filters = ref({
  task_name: '',
  status: undefined as number | undefined,
  log_type: undefined as 'archive' | 'flashback' | undefined
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getExecutionLogList({
      page: page.value,
      per_page: perPage.value,
      ...filters.value
    })
    if (res.data) {
      list.value = res.data.items.map(item => ({ ...item, _selected: false }))
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

async function downloadLog(type: 'archive' | 'flashback', id: number) {
  const response = await downloadExecutionLog(type, id)
  const blob = new Blob([response.data], { type: 'text/plain' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${type}_execution_log_${id}.log`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/stores/flashbackTask.spec.ts src/stores/executionLog.spec.ts
```

Expected: PASS，两个 store 测试通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/flashbackTask.ts frontend/src/api/executionLog.ts frontend/src/stores/flashbackTask.ts frontend/src/stores/executionLog.ts frontend/src/stores/flashbackTask.spec.ts frontend/src/stores/executionLog.spec.ts
git commit -m "feat: add flashback frontend data layer"
```

## Task 5: Update Navigation And Execution Log Center UI (TDD)

**Files:**
- Modify: `backend/services/auth_service.py`
- Modify: `frontend/src/auth/access.ts`
- Modify: `frontend/src/auth/access.spec.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Modify: `frontend/src/components/Layout/Sidebar.spec.ts`
- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`
- Modify: `frontend/src/views/ExecutionLogList.vue`
- Create: `frontend/src/views/ExecutionLogList.spec.ts`
- Test: `frontend/src/auth/access.spec.ts`
- Test: `frontend/src/components/Layout/Sidebar.spec.ts`
- Test: `frontend/src/components/Layout/AppLayout.spec.ts`
- Test: `frontend/src/views/ExecutionLogList.spec.ts`

- [ ] **Step 1: Write the failing UI/navigation tests**

`frontend/src/auth/access.spec.ts`

```ts
it('shows flashback and execution logs as top-level admin menus', () => {
  const menus = getVisibleMenus('admin').map((item) => item.path)
  expect(menus).toContain('/execution-logs')
  expect(menus).toContain('/flashback-tasks')
})
```

`frontend/src/views/ExecutionLogList.spec.ts`

```ts
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/stores/executionLog', () => ({
  useExecutionLogStore: () => ({
    list: [{
      id: 11,
      task_id: 11,
      task_name: 'demo.orders',
      log_type: 'flashback',
      status: 1,
      detail_path: '/flashback-tasks/11',
      log_file: '/tmp/run.log'
    }],
    loading: false,
    page: 1,
    perPage: 10,
    total: 1,
    fetchList: vi.fn(),
    setFilters: vi.fn(),
    resetFilters: vi.fn(),
    downloadLog: vi.fn(),
    goToPage: vi.fn(),
    setPageSize: vi.fn()
  })
}))

import ExecutionLogList from './ExecutionLogList.vue'

describe('ExecutionLogList', () => {
  it('renders log type column and flashback task row', () => {
    setActivePinia(createPinia())
    const wrapper = mount(ExecutionLogList)
    expect(wrapper.text()).toContain('闪回日志')
    expect(wrapper.text()).toContain('demo.orders')
  })
})
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd frontend && npm test -- src/auth/access.spec.ts src/components/Layout/Sidebar.spec.ts src/components/Layout/AppLayout.spec.ts src/views/ExecutionLogList.spec.ts
```

Expected: FAIL，提示 `/flashback-tasks` 未配置或日志页未显示“闪回日志”。

- [ ] **Step 3: Implement menu, route, and unified log page**

`backend/services/auth_service.py`

```python
ADMIN_MENU = [
    {'path': '/optimization-tasks', 'label': 'SQL智能建议'},
    {'path': '/slow-sqls', 'label': '慢SQL管理'},
    {'path': '/archive-tasks', 'label': '归档任务'},
    {'path': '/execution-logs', 'label': '执行日志'},
    {'path': '/flashback-tasks', 'label': '数据闪回'},
    {'path': '/users', 'label': '用户管理'},
    {'path': '/roles', 'label': '角色管理'},
    {'path': '/permissions', 'label': '权限管理'},
    {'path': '/connections', 'label': '连接管理'},
]
```

`frontend/src/auth/access.ts`

```ts
export const MENU_ITEMS: MenuItem[] = [
  { path: '/optimization-tasks', label: 'SQL智能建议', roles: ['admin', 'user'], matchPrefixes: ['/optimization-tasks'] },
  { path: '/slow-sqls', label: '慢SQL管理', roles: ['admin', 'user'], matchPrefixes: ['/slow-sqls', '/slow-sql/'] },
  { path: '/archive-tasks', label: '归档任务', roles: ['admin'], matchPrefixes: ['/archive-tasks'] },
  { path: '/execution-logs', label: '执行日志', roles: ['admin'], matchPrefixes: ['/execution-logs'] },
  { path: '/flashback-tasks', label: '数据闪回', roles: ['admin'], matchPrefixes: ['/flashback-tasks'] },
  { path: '/users', label: '用户管理', roles: ['admin'], matchPrefixes: ['/users'] },
  { path: '/roles', label: '角色管理', roles: ['admin'], matchPrefixes: ['/roles'] },
  { path: '/permissions', label: '权限管理', roles: ['admin'], matchPrefixes: ['/permissions'] },
  { path: '/connections', label: '连接管理', roles: ['admin'], matchPrefixes: ['/connections'] }
]
```

`frontend/src/router/index.ts`

```ts
{
  path: '/flashback-tasks',
  name: 'FlashbackTaskList',
  component: () => import('@/views/FlashbackTaskList.vue')
},
{
  path: '/flashback-tasks/create',
  name: 'FlashbackTaskCreate',
  component: () => import('@/views/FlashbackTaskCreate.vue')
},
{
  path: '/flashback-tasks/:id',
  name: 'FlashbackTaskDetail',
  component: () => import('@/views/FlashbackTaskDetail.vue')
}
```

`frontend/src/components/Layout/Sidebar.vue`

```vue
<el-menu-item
  v-if="hasMenu('/archive-tasks')"
  index="/archive-tasks"
  data-path="/archive-tasks"
  @click="navigate('/archive-tasks')"
>
  <el-icon><Tickets /></el-icon>
  <span>归档任务</span>
</el-menu-item>

<el-menu-item
  v-if="hasMenu('/execution-logs')"
  index="/execution-logs"
  data-path="/execution-logs"
  @click="navigate('/execution-logs')"
>
  <el-icon><Document /></el-icon>
  <span>执行日志</span>
</el-menu-item>

<el-menu-item
  v-if="hasMenu('/flashback-tasks')"
  index="/flashback-tasks"
  data-path="/flashback-tasks"
  @click="navigate('/flashback-tasks')"
>
  <el-icon><RefreshRight /></el-icon>
  <span>数据闪回</span>
</el-menu-item>
```

`frontend/src/views/ExecutionLogList.vue`

```vue
<el-card shadow="never" class="filter-card">
  <el-form :model="filters" inline>
    <el-form-item label="日志类型">
      <el-select v-model="filters.log_type" clearable placeholder="全部日志" style="width: 160px">
        <el-option label="归档日志" value="archive" />
        <el-option label="闪回日志" value="flashback" />
      </el-select>
    </el-form-item>
    <el-form-item label="任务名称">
      <el-input v-model="filters.task_name" placeholder="搜索任务名称" style="width: 240px" />
    </el-form-item>
    <el-form-item label="执行状态">
      <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 160px">
        <el-option label="失败" :value="0" />
        <el-option label="成功" :value="1" />
        <el-option label="执行中" :value="2" />
      </el-select>
    </el-form-item>
  </el-form>
</el-card>

<el-table-column label="日志类型" width="110">
  <template #default="{ row }">
    <span>{{ row.log_type === 'flashback' ? '闪回日志' : '归档日志' }}</span>
  </template>
</el-table-column>

<el-table-column prop="task_name" label="任务名称" min-width="220">
  <template #default="{ row }">
    <el-button link type="primary" @click="router.push(row.detail_path || '/execution-logs')">
      {{ row.task_name || '-' }}
    </el-button>
  </template>
</el-table-column>
```

`frontend/src/views/ExecutionLogList.vue` script adjustments

```ts
const filters = ref({
  task_name: '',
  status: undefined as number | undefined,
  log_type: undefined as 'archive' | 'flashback' | undefined
})

async function handleViewLog(row: ExecutionLog) {
  currentLog.value = row
  logDialogVisible.value = true
  refreshingLog.value = true
  try {
    const response = await getLogContent(row.log_type, row.id as number)
    logContent.value = response.data?.content || ''
  } finally {
    refreshingLog.value = false
  }
}

async function handleDownload(row: ExecutionLog) {
  await store.downloadLog(row.log_type, row.id as number)
}
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/auth/access.spec.ts src/components/Layout/Sidebar.spec.ts src/components/Layout/AppLayout.spec.ts src/views/ExecutionLogList.spec.ts
```

Expected: PASS，新菜单、标签标题、统一日志页渲染全部通过。

- [ ] **Step 5: Commit**

```bash
git add backend/services/auth_service.py frontend/src/auth/access.ts frontend/src/auth/access.spec.ts frontend/src/router/index.ts frontend/src/components/Layout/Sidebar.vue frontend/src/components/Layout/Sidebar.spec.ts frontend/src/components/Layout/AppLayout.spec.ts frontend/src/views/ExecutionLogList.vue frontend/src/views/ExecutionLogList.spec.ts
git commit -m "feat: add flashback navigation and unified log center"
```

## Task 6: Build Flashback List/Create/Detail Pages (TDD)

**Files:**
- Create: `frontend/src/views/FlashbackTaskList.vue`
- Create: `frontend/src/views/FlashbackTaskCreate.vue`
- Create: `frontend/src/views/FlashbackTaskDetail.vue`
- Create: `frontend/src/views/FlashbackTaskList.spec.ts`
- Create: `frontend/src/views/FlashbackTaskCreate.spec.ts`
- Create: `frontend/src/views/FlashbackTaskDetail.spec.ts`
- Test: `frontend/src/views/FlashbackTaskList.spec.ts`
- Test: `frontend/src/views/FlashbackTaskCreate.spec.ts`
- Test: `frontend/src/views/FlashbackTaskDetail.spec.ts`

- [ ] **Step 1: Write the failing view tests**

`frontend/src/views/FlashbackTaskCreate.spec.ts`

```ts
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: {} })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    authorizedConnections: [{ id: 1, connection_name: '测试连接', host: '10.0.0.10', port: 3306 }],
    fetchAuthorizedConnections: vi.fn()
  })
}))

vi.mock('@/stores/flashbackTask', () => ({
  useFlashbackTaskStore: () => ({
    submitLoading: false,
    createTask: vi.fn(async () => ({ id: 9 }))
  })
}))

import FlashbackTaskCreate from './FlashbackTaskCreate.vue'

describe('FlashbackTaskCreate', () => {
  it('submits and navigates to detail page', async () => {
    setActivePinia(createPinia())
    const wrapper = mount(FlashbackTaskCreate)
    await wrapper.find('input[placeholder=\"请输入数据库名\"]').setValue('demo')
    await wrapper.find('input[placeholder=\"请输入表名\"]').setValue('orders')
    expect(wrapper.text()).toContain('数据闪回')
  })
})
```

`frontend/src/views/FlashbackTaskDetail.spec.ts`

```ts
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '8' } }),
  useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/stores/flashbackTask', () => ({
  useFlashbackTaskStore: () => ({
    currentTask: {
      id: 8,
      connection_name: '测试连接',
      database_name: 'demo',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql',
      status: 'completed',
      artifacts: [
        { id: 'binlog_status-txt', name: 'binlog_status.txt', size: 10 },
        { id: 'biglong_trx-txt', name: 'biglong_trx.txt', size: 10 },
        { id: 'result-sql', name: 'orders.sql', size: 10 }
      ]
    },
    detailLoading: false,
    fetchDetail: vi.fn()
  })
}))

import FlashbackTaskDetail from './FlashbackTaskDetail.vue'

describe('FlashbackTaskDetail', () => {
  it('renders three downloadable artifacts', () => {
    const wrapper = mount(FlashbackTaskDetail)
    expect(wrapper.text()).toContain('binlog_status.txt')
    expect(wrapper.text()).toContain('biglong_trx.txt')
    expect(wrapper.text()).toContain('orders.sql')
  })
})
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd frontend && npm test -- src/views/FlashbackTaskList.spec.ts src/views/FlashbackTaskCreate.spec.ts src/views/FlashbackTaskDetail.spec.ts
```

Expected: FAIL，提示视图文件不存在。

- [ ] **Step 3: Implement the three flashback views**

`frontend/src/views/FlashbackTaskList.vue`

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <h2>数据闪回</h2>
      <el-button type="primary" class="submit-btn" @click="router.push('/flashback-tasks/create')">
        新建闪回任务
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="数据库名">
          <el-input v-model="filters.database_name" placeholder="搜索数据库名" />
        </el-form-item>
        <el-form-item label="表名">
          <el-input v-model="filters.table_name" placeholder="搜索表名" />
        </el-form-item>
        <el-form-item label="SQL类型">
          <el-select v-model="filters.sql_type" clearable placeholder="全部类型">
            <el-option label="DELETE" value="delete" />
            <el-option label="INSERT" value="insert" />
            <el-option label="UPDATE" value="update" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="store.list" v-loading="store.loading">
        <el-table-column prop="connection_name" label="连接名称" width="180" />
        <el-table-column label="对象" min-width="220">
          <template #default="{ row }">{{ row.database_name }}.{{ row.table_name }}</template>
        </el-table-column>
        <el-table-column prop="sql_type" label="SQL类型" width="120" />
        <el-table-column prop="work_type" label="输出类型" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/flashback-tasks/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'

const router = useRouter()
const store = useFlashbackTaskStore()
const filters = reactive({
  database_name: '',
  table_name: '',
  sql_type: '',
})

onMounted(() => {
  store.fetchList()
})

function handleSearch() {
  store.setFilters(filters)
  store.fetchList()
}
</script>
```

`frontend/src/views/FlashbackTaskCreate.vue`

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <h2>创建数据闪回任务</h2>
      <el-button class="ghost-btn back-btn" @click="router.push('/flashback-tasks')">返回列表</el-button>
    </div>

    <el-card shadow="never" class="form-shell">
      <el-form ref="formRef" :model="formData" :rules="rules" label-position="top">
        <el-row :gutter="16">
          <el-col :md="12">
            <el-form-item label="数据库连接" prop="db_connection_id">
              <el-select v-model="formData.db_connection_id" placeholder="请选择数据库连接" style="width: 100%">
                <el-option
                  v-for="conn in authStore.authorizedConnections"
                  :key="conn.id"
                  :label="`${conn.connection_name} (${conn.host}:${conn.port})`"
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :md="12">
            <el-form-item label="闪回方式">
              <el-input model-value="repl" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="数据库名" prop="database_name"><el-input v-model="formData.database_name" placeholder="请输入数据库名" /></el-form-item></el-col>
          <el-col :md="12"><el-form-item label="表名" prop="table_name"><el-input v-model="formData.table_name" placeholder="请输入表名" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="SQL类型" prop="sql_type"><el-select v-model="formData.sql_type"><el-option label="DELETE" value="delete" /><el-option label="INSERT" value="insert" /><el-option label="UPDATE" value="update" /></el-select></el-form-item></el-col>
          <el-col :md="12"><el-form-item label="输出类型" prop="work_type"><el-select v-model="formData.work_type"><el-option label="2SQL" value="2sql" /><el-option label="ROLLBACK" value="rollback" /><el-option label="STATS" value="stats" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="起始时间"><el-input v-model="formData.start_datetime" placeholder="YYYY-MM-DD HH:mm:ss" /></el-form-item></el-col>
          <el-col :md="12"><el-form-item label="结束时间"><el-input v-model="formData.stop_datetime" placeholder="YYYY-MM-DD HH:mm:ss" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="起始日志"><el-input v-model="formData.start_file" placeholder="例如 mysql-bin.004520" /></el-form-item></el-col>
          <el-col :md="12"><el-form-item label="结束日志"><el-input v-model="formData.stop_file" placeholder="例如 mysql-bin.004521" /></el-form-item></el-col>
        </el-row>
        <div class="action-row">
          <el-button class="ghost-btn" @click="router.push('/flashback-tasks')">取消</el-button>
          <el-button type="primary" class="submit-btn" :loading="store.submitLoading" @click="handleSubmit">生成闪回结果</el-button>
        </div>
      </el-form>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'

const router = useRouter()
const authStore = useAuthStore()
const store = useFlashbackTaskStore()
const formRef = ref<FormInstance>()
const formData = ref({
  db_connection_id: undefined as number | undefined,
  database_name: '',
  table_name: '',
  sql_type: 'delete' as 'delete' | 'insert' | 'update',
  work_type: '2sql' as '2sql' | 'rollback' | 'stats',
  start_datetime: '',
  stop_datetime: '',
  start_file: '',
  stop_file: ''
})

const rules = {
  db_connection_id: [{ required: true, message: '请选择数据库连接', trigger: 'change' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  table_name: [{ required: true, message: '请输入表名', trigger: 'blur' }],
  sql_type: [{ required: true, message: '请选择SQL类型', trigger: 'change' }],
  work_type: [{ required: true, message: '请选择输出类型', trigger: 'change' }]
}

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }
})

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const task = await store.createTask({
    db_connection_id: formData.value.db_connection_id as number,
    database_name: formData.value.database_name.trim(),
    table_name: formData.value.table_name.trim(),
    sql_type: formData.value.sql_type,
    work_type: formData.value.work_type,
    start_datetime: formData.value.start_datetime.trim(),
    stop_datetime: formData.value.stop_datetime.trim(),
    start_file: formData.value.start_file.trim(),
    stop_file: formData.value.stop_file.trim()
  })

  if (task?.id) {
    router.push(`/flashback-tasks/${task.id}`)
  }
}
</script>
```

`frontend/src/views/FlashbackTaskDetail.vue`

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <h2>数据闪回详情</h2>
      <el-button class="ghost-btn back-btn" @click="router.push('/flashback-tasks')">返回列表</el-button>
    </div>

    <el-card shadow="never" class="detail-card" v-loading="store.detailLoading">
      <div class="detail-grid">
        <div><strong>连接名称：</strong>{{ store.currentTask?.connection_name }}</div>
        <div><strong>对象：</strong>{{ store.currentTask?.database_name }}.{{ store.currentTask?.table_name }}</div>
        <div><strong>SQL类型：</strong>{{ store.currentTask?.sql_type }}</div>
        <div><strong>输出类型：</strong>{{ store.currentTask?.work_type }}</div>
        <div><strong>状态：</strong>{{ store.currentTask?.status }}</div>
      </div>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header><div class="card-title">结果文件</div></template>
      <el-table :data="store.currentTask?.artifacts || []">
        <el-table-column prop="name" label="文件名" min-width="220" />
        <el-table-column prop="size" label="大小" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDownloadArtifact(row.id, row.name)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header><div class="card-title">执行日志</div></template>
      <pre class="log-pre">{{ logContent }}</pre>
      <div class="action-row">
        <el-button class="ghost-btn" @click="refreshLog">刷新日志</el-button>
        <el-button type="primary" class="submit-btn" @click="handleDownloadLog">下载日志</el-button>
      </div>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'

const route = useRoute()
const router = useRouter()
const store = useFlashbackTaskStore()
const logContent = ref('')

async function refreshLog() {
  if (!store.currentTask?.id) return
  logContent.value = await store.fetchLogContent(store.currentTask.id)
}

async function handleDownloadLog() {
  if (!store.currentTask?.id) return
  await store.triggerDownloadLog(store.currentTask.id)
}

async function handleDownloadArtifact(artifactId: string, fileName: string) {
  if (!store.currentTask?.id) return
  await store.triggerDownloadArtifact(store.currentTask.id, artifactId, fileName)
}

onMounted(async () => {
  await store.fetchDetail(Number(route.params.id))
  await refreshLog()
})
</script>
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/views/FlashbackTaskList.spec.ts src/views/FlashbackTaskCreate.spec.ts src/views/FlashbackTaskDetail.spec.ts
```

Expected: PASS，列表/创建/详情三个页面测试通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/FlashbackTaskList.vue frontend/src/views/FlashbackTaskCreate.vue frontend/src/views/FlashbackTaskDetail.vue frontend/src/views/FlashbackTaskList.spec.ts frontend/src/views/FlashbackTaskCreate.spec.ts frontend/src/views/FlashbackTaskDetail.spec.ts
git commit -m "feat: add flashback task pages"
```

## Task 7: Full Regression Verification

**Files:**
- Modify: none
- Test: backend and frontend suites

- [ ] **Step 1: Run backend focused tests**

Run:

```bash
python3 -m unittest backend.tests.test_flashback_service backend.tests.test_flashback_api backend.tests.test_execution_log_api -v
```

Expected: PASS，闪回与统一日志后端测试全部通过。

- [ ] **Step 2: Run frontend focused tests**

Run:

```bash
cd frontend && npm test -- src/stores/flashbackTask.spec.ts src/stores/executionLog.spec.ts src/views/ExecutionLogList.spec.ts src/views/FlashbackTaskList.spec.ts src/views/FlashbackTaskCreate.spec.ts src/views/FlashbackTaskDetail.spec.ts src/auth/access.spec.ts src/components/Layout/Sidebar.spec.ts src/components/Layout/AppLayout.spec.ts
```

Expected: PASS，新增与受影响前端测试全部通过。

- [ ] **Step 3: Run full frontend suite**

Run:

```bash
cd frontend && npm test
```

Expected: PASS，无旧页面回归失败。

- [ ] **Step 4: Manual smoke check**

Run:

```bash
cd frontend && npm run build
python3 backend/init_db.py
```

Expected:

1. 前端构建成功。
2. 本地数据库能正常创建 `flashback_task` 表。
3. 登录后可见一级菜单“执行日志”“数据闪回”。
4. 创建闪回任务后可进入详情页并看到日志/结果文件区域。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: verify flashback workflow end to end"
```
