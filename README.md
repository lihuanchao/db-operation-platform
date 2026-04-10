# 数据库运维管理平台

## 项目简介

这是一个面向 MySQL 运维场景的管理平台，提供以下核心能力：

- `SQL优化`：SQL/MyBatis 优化任务创建、执行、详情查看与结果下载
- `SQL巡检`：慢 SQL 列表筛选、详情分析、优化建议与报告下载
- `归档任务`：归档任务配置、立即执行、定时任务管理（Cron）
- `数据闪回`：基于 `my2sql` 异步生成闪回结果文件与日志
- `执行日志`：统一查看归档日志与闪回日志，支持日志内容查看与下载
- `系统管理`：用户管理、角色管理、连接授权（权限管理）
- `连接管理`：数据库连接配置、测试、启停

## 技术栈

### 后端

- Flask 3.0
- Flask-SQLAlchemy 3.1
- APScheduler 3.10
- PyMySQL 1.1
- Cryptography 41

### 前端

- Vue 3 + TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Axios

## 主要页面（当前菜单）

- SQL优化
- SQL巡检
- 归档任务
- 数据闪回
- 执行日志
- 系统管理
  - 用户管理
  - 角色管理
  - 权限管理
- 连接管理

## 目录结构（简化）

```text
claude-project/
├── backend/
│   ├── app.py
│   ├── init_db.py
│   ├── models/
│   │   ├── slow_sql.py
│   │   ├── optimization_task.py
│   │   ├── flashback_task.py
│   │   ├── archive_task.py
│   │   ├── cron_job.py
│   │   ├── execution_log.py
│   │   ├── sys_user.py
│   │   └── user_connection_permission.py
│   ├── services/
│   │   ├── slow_sql_service.py
│   │   ├── optimization_task_service.py
│   │   ├── flashback_service.py
│   │   ├── archive_service.py
│   │   ├── cron_service.py
│   │   ├── execution_log_service.py
│   │   ├── auth_service.py
│   │   ├── user_admin_service.py
│   │   └── pt_archiver.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── api/
│   │   ├── stores/
│   │   ├── router/
│   │   └── types/
│   └── package.json
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── nginx.conf
```

## 环境要求

- Python `3.12+`
- Node.js `20+`
- MySQL `8.0+`（生产/联调）
- `my2sql` 可执行文件（数据闪回功能）

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python app.py
```

默认监听：`http://127.0.0.1:5000`

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

默认监听：`http://127.0.0.1:5173`

## 配置说明

后端支持通过 `backend/.env` 配置数据库与应用参数，常用项：

```env
DATABASE_URL=mysql://user:password@host:3306/dbname
SECRET_KEY=replace_with_your_secret
DASHSCOPE_API_KEY=replace_with_your_api_key
```

## 数据闪回（my2sql）说明

当前代码中数据闪回能力由 `FlashbackService` 调用本地 `my2sql`：

- 工具路径固定为：`/my2sql`
- 输出目录根路径：`/app/flashback/tasks`
- 结果文件支持下载：
  - 固定文件：`binlog_status.txt`
  - 固定文件：`biglong_trx.txt`
  - 动态文件：`*.sql`

如果本机 `my2sql` 不在 `/my2sql`，请修改：

- `backend/services/flashback_service.py`
  - `TOOL_PATH`
  - `OUTPUT_ROOT`

## 关键后端接口（节选）

### 认证与授权

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/connections`（当前用户可用连接）

### SQL优化/SQL巡检

- `GET /api/optimization-tasks`
- `POST /api/optimization-tasks/sql`
- `POST /api/optimization-tasks/mybatis`
- `GET /api/optimization-tasks/<id>`
- `GET /api/slow-sqls`
- `GET /api/slow-sqls/<checksum>`
- `POST /api/slow-sqls/<checksum>/optimize`
- `POST /api/slow-sqls/batch-optimize`
- `GET /api/slow-sqls/<checksum>/download`

### 数据闪回

- `GET /api/flashback-tasks`
- `POST /api/flashback-tasks`
- `GET /api/flashback-tasks/<id>`
- `GET /api/flashback-tasks/<id>/artifacts`
- `GET /api/flashback-tasks/<id>/artifacts/<artifact_id>/download`

### 归档与定时

- `GET /api/archive-tasks`
- `POST /api/archive-tasks`
- `GET /api/archive-tasks/<id>`
- `PUT /api/archive-tasks/<id>`
- `DELETE /api/archive-tasks/<id>`
- `POST /api/archive-tasks/<id>/execute`
- `GET /api/cron-jobs`
- `POST /api/cron-jobs`
- `PUT /api/cron-jobs/<id>`
- `DELETE /api/cron-jobs/<id>`
- `POST /api/cron-jobs/<id>/toggle`

### 执行日志中心

- `GET /api/execution-logs`
- `GET /api/execution-logs/<id>`
- `GET /api/execution-logs/<int:id>/download`
- `GET /api/execution-logs/<string:log_type>/<int:id>/download`
- `GET /api/execution-logs/<int:id>/log-content`
- `GET /api/execution-logs/<string:log_type>/<int:id>/log-content`

### 管理端（管理员）

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/<user_id>`
- `PUT /api/admin/users/<user_id>/status`
- `PUT /api/admin/users/<user_id>/reset-password`
- `DELETE /api/admin/users/<user_id>`
- `GET /api/admin/roles`
- `GET /api/admin/user-connection-permissions/<user_id>`
- `PUT /api/admin/user-connection-permissions/<user_id>`
- `GET /api/connections`
- `POST /api/connections`
- `PUT /api/connections/<id>`
- `DELETE /api/connections/<id>`
- `POST /api/connections/test-direct`
- `POST /api/connections/<id>/test`

## 测试

### 前端

```bash
cd frontend
npm test
```

### 后端

```bash
cd backend
python -m unittest discover -s tests -p "test_*.py" -v
```

## 备注

- 前端保留了 `/flashback-tasks/create` 路由用于兼容，但当前主流程已改为在“数据闪回任务”列表页通过弹窗创建任务。
- 执行日志已统一归档任务与闪回任务，不再分离入口。
