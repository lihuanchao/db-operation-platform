# My2SQL Data Flashback Design

## 1. 背景与目标

当前系统已有 SQL 智能建议、慢 SQL 管理、归档管理、执行日志等能力，但缺少对 MySQL 误删、误更新、误插入场景的“数据闪回”支持。  
本次新增功能目标是在现有系统中接入 `my2sql` 工具，为管理员提供一个“生成闪回结果文件”的能力：用户提交参数后，系统异步调用 `/my2sql` 生成结果文件与执行日志，并提供在线查看与下载。

### 目标

1. 新增“数据闪回”功能入口，支持创建一次性闪回生成任务。
2. 支持基于已配置数据库连接自动填充 `host`、`port`、`user`、`password`。
3. 支持用户输入数据库名、表名，选择 SQL 类型与输出类型。
4. 支持可选时间范围与 binlog 文件范围参数，空值时执行命令不带对应参数。
5. 后台异步执行 `/my2sql`，记录任务状态、执行日志、生成文件清单。
6. 固定识别并提供 3 个结果文件下载：
   - `binlog_status.txt`
   - `biglong_trx.txt`
   - 任意一个以 `.sql` 结尾的结果文件
7. 页面可查看执行日志，并下载日志与结果文件。
8. 左侧导航中“数据闪回”作为独立一级菜单展示。
9. “执行日志”作为独立一级菜单展示，并统一查看归档日志与闪回日志。

### 非目标

1. 本期不支持页面内直接执行回滚或回放到数据库。
2. 本期不做定时执行、周期任务、审批流。
3. 本期不支持多表批量提交。
4. 本期不开放给普通用户，仅面向管理员。

## 2. 方案概览

推荐采用“独立一次性任务模型 + 后台线程异步执行”的方案：

1. 不复用现有 `ArchiveTask + ExecutionLog` 模型。
2. 新增独立的 `FlashbackTask` 模型，承载参数、状态、日志路径、输出目录、结果文件清单。
3. 后端新增 `FlashbackService`，负责参数校验、命令构建、任务创建、异步执行、结果采集。
4. 前端新增 3 个页面：
   - 数据闪回列表页
   - 创建数据闪回任务页
   - 数据闪回详情页
5. 改造现有“执行日志”页面为统一日志中心，同时展示归档日志与闪回日志。
6. 交互模式对齐现有“SQL 智能建议”页面风格：列表页作为入口与历史记录中心，创建页负责参数提交，详情页负责结果查看与下载。

采用该方案的主要原因：

1. 现有 `ExecutionLog` 与 `ArchiveTask` 强绑定，直接复用会让闪回任务与归档任务语义混淆。
2. 闪回需求更接近 `OptimizationTask` 的“一次提交、后台异步、列表查看结果”模式。
3. 独立模型更利于后续扩展，例如审批、留痕、结果保留期限、审计字段。

## 3. 信息架构与页面设计

### 3.1 导航位置

左侧导航调整为独立一级菜单：

1. `归档任务`
2. `执行日志`
3. `数据闪回`

其中：

1. `归档任务` 保持独立菜单。
2. `执行日志` 从原归档相关分组中拆出，变为独立菜单。
3. `数据闪回` 不放入“归档管理”分组，直接作为独立菜单。
4. 三者均仅 `admin` 可见。

### 3.2 执行日志页

用途：作为统一日志中心，集中查看归档任务执行日志和闪回任务执行日志。

页面结构：

1. 顶部筛选卡片
   - 日志类型：全部 / 归档日志 / 闪回日志
   - 任务名称
   - 执行状态
   - 创建时间范围
2. 日志列表卡片
   - 日志类型
   - 任务名称
   - 执行状态
   - 开始时间
   - 结束时间
   - 日志文件
   - 错误信息
   - 操作

日志类型说明：

1. `归档日志`：来自现有 `ExecutionLog`
2. `闪回日志`：由 `FlashbackTask` 映射生成统一日志项

操作项：

1. 查看日志
2. 下载日志

交互规则：

1. 默认显示全部日志
2. 支持按日志类型快速筛选
3. 点击日志可跳转对应任务详情页
4. 归档日志跳转到归档任务上下文
5. 闪回日志跳转到闪回任务详情页

### 3.3 数据闪回列表页

用途：展示历史任务、筛选任务、进入创建页、进入详情页。

页面结构：

1. 顶部筛选卡片
   - 连接
   - 数据库名
   - 表名
   - SQL 类型
   - 输出类型
   - 状态
   - 创建时间范围
2. 历史任务列表卡片
   - 任务 ID
   - 连接名称
   - 数据库/表
   - SQL 类型
   - 输出类型
   - 状态
   - 创建人
   - 创建时间
   - 完成时间
   - 操作
3. 页面主操作
   - `新建闪回任务`

操作项：

1. 查看详情
2. 下载日志（任务完成或失败后可用）

### 3.4 创建数据闪回任务页

用途：录入参数并提交生成任务。

表单字段：

1. 数据库连接：下拉选择，来源于当前用户可访问连接
2. 数据库名：手动输入
3. 表名：手动输入
4. 闪回方式：固定 `repl`，只读展示
5. SQL 类型：`delete` / `insert` / `update`
6. 起始时间：可空
7. 结束时间：可空
8. 起始日志：可空
9. 结束日志：可空
10. 输出类型：`2sql` / `rollback` / `stats`

隐藏规则：

1. `host`、`port` 不作为可编辑项，可在“连接摘要”区域展示。
2. `username`、`password` 不在页面展示，不返回给前端。
3. `output_dir` 不允许用户指定，由系统自动生成。

提交后行为：

1. 创建任务记录
2. 立即进入后台执行
3. 前端跳转任务详情页

### 3.5 数据闪回详情页

用途：查看任务参数、状态、结果文件与执行日志。

页面结构：

1. 任务摘要卡片
   - 连接名称
   - 数据库名
   - 表名
   - SQL 类型
   - 输出类型
   - 闪回方式
   - 起止时间
   - 起止日志文件
   - 创建人
   - 创建时间
   - 开始时间
   - 完成时间
2. 结果文件卡片
   - `binlog_status.txt`
   - `biglong_trx.txt`
   - `*.sql`
   - 文件大小
   - 下载按钮
3. 执行日志卡片
   - 日志实时内容
   - 刷新日志
   - 下载日志
4. 命令预览卡片
   - 展示脱敏后的命令字符串
   - `password` 显示为 `******`

状态规则：

1. `queued`：等待执行
2. `running`：执行中
3. `completed`：执行成功并已完成产物采集
4. `failed`：执行失败或结果文件校验失败

## 4. 参数与命令映射

执行命令以 `/my2sql` 为固定二进制路径，参数映射如下：

```bash
/my2sql \
  -databases {database_name} \
  -tables {table_name} \
  -mode repl \
  -host {host} \
  -port {port} \
  -user {username} \
  -password {password} \
  -sql {sql_type} \
  [-start-datetime "{start_datetime}"] \
  [-stop-datetime "{stop_datetime}"] \
  [-start-file {start_file}] \
  [-stop-file {stop_file}] \
  -work-type {work_type} \
  -output-dir {task_output_dir}
```

### 参数规则

1. `-databases`：来自用户输入，必填
2. `-tables`：来自用户输入，必填
3. `-mode`：固定 `repl`
4. `-host`：来自连接 `host`
5. `-port`：来自连接 `port`
6. `-user`：来自连接 `username`
7. `-password`：来自连接解密后的密码
8. `-sql`：`delete` / `insert` / `update`
9. `-start-datetime`：可空，空则不拼接
10. `-stop-datetime`：可空，空则不拼接
11. `-start-file`：可空，空则不拼接
12. `-stop-file`：可空，空则不拼接
13. `-work-type`：`2sql` / `rollback` / `stats`
14. `-output-dir`：系统生成任务专属目录

## 5. 数据模型设计

新增表：`flashback_task`

建议字段：

1. `id`
2. `db_connection_id`
3. `connection_id`
4. `connection_name`
5. `database_name`
6. `table_name`
7. `mode`
8. `sql_type`
9. `work_type`
10. `start_datetime`
11. `stop_datetime`
12. `start_file`
13. `stop_file`
14. `status`
15. `progress`
16. `output_dir`
17. `log_file`
18. `masked_command`
19. `artifact_manifest`
20. `error_message`
21. `creator_user_id`
22. `creator_employee_no`
23. `created_at`
24. `updated_at`
25. `started_at`
26. `finished_at`

### 字段说明

1. `artifact_manifest` 使用 JSON 字符串或 JSON 字段，记录结果文件清单。
2. `masked_command` 保存脱敏后的完整命令，供详情页展示与排障。
3. `progress` 为页面轮询和状态展示预留，阶段值可简化为 `0/30/70/100`。
4. `connection_id` 用于权限过滤，保持与现有优化任务一致。
5. 每个 `FlashbackTask` 同时承担一条“闪回日志源记录”的职责，不额外新增独立日志表。

### artifact_manifest 结构

```json
[
  {
    "id": "binlog-status",
    "name": "binlog_status.txt",
    "path": "/app/flashback/tasks/101/output/binlog_status.txt",
    "size": 2048
  },
  {
    "id": "biglong-trx",
    "name": "biglong_trx.txt",
    "path": "/app/flashback/tasks/101/output/biglong_trx.txt",
    "size": 1024
  },
  {
    "id": "result-sql",
    "name": "flashback_delete_20260408.sql",
    "path": "/app/flashback/tasks/101/output/flashback_delete_20260408.sql",
    "size": 40960
  }
]
```

## 6. 文件与日志落盘设计

每个任务创建独立目录，例如：

```text
/app/flashback/tasks/{task_id}/
  run.log
  output/
    binlog_status.txt
    biglong_trx.txt
    xxx.sql
```

### 日志要求

`run.log` 至少记录：

1. 任务开始时间
2. 脱敏命令
3. 实际输出目录
4. 标准输出与标准错误
5. 退出码
6. 产物扫描结果
7. 失败原因

### 结果文件识别规则

任务结束后由后端扫描 `output_dir`，要求识别：

1. 固定文件 `binlog_status.txt`
2. 固定文件 `biglong_trx.txt`
3. 任意一个以 `.sql` 结尾的文件

处理规则：

1. 三个文件都存在时，任务可标记为 `completed`
2. 若命令退出成功但结果文件不完整，任务标记为 `failed`
3. `artifact_manifest` 只登记上述 3 个对外展示文件
4. 若存在多个 `.sql` 文件，按文件名升序排序后取第一个登记为对外下载文件，其余文件只在日志中记录

## 7. 后端架构设计

### 7.1 模型层

新增：

1. `backend/models/flashback_task.py`

调整：

1. `backend/models/__init__.py` 导出新模型

### 7.2 服务层

新增：

1. `backend/services/flashback_service.py`

职责拆分：

1. `create_task(data, current_user)`：校验、建任务、落库、启动后台线程
2. `get_task_list(...)`：列表查询与权限过滤
3. `get_task_detail(task_id, current_user)`：详情查询
4. `_build_command(task, connection)`：构建实际命令与脱敏命令
5. `_run_task_async(task_id)`：启动后台线程
6. `_execute_task(task_id)`：执行 `/my2sql`、写日志、扫描产物、更新状态
7. `get_log_content(task_id, current_user)`：读取日志内容
8. `download_log(task_id, current_user)`：下载日志
9. `download_artifact(task_id, artifact_id, current_user)`：下载结果文件

### 7.3 API 层

新增接口：

1. `GET /api/flashback-tasks`
2. `POST /api/flashback-tasks`
3. `GET /api/flashback-tasks/<id>`
4. `GET /api/flashback-tasks/<id>/log-content`
5. `GET /api/flashback-tasks/<id>/download-log`
6. `GET /api/flashback-tasks/<id>/artifacts`
7. `GET /api/flashback-tasks/<id>/artifacts/<artifact_id>/download`

调整接口：

1. `GET /api/execution-logs`
   - 新增 `log_type` 参数：`archive` / `flashback` / 空
   - 返回统一日志列表
2. `GET /api/execution-logs/<type>/<id>/log-content`
   - 支持读取归档日志或闪回日志
3. `GET /api/execution-logs/<type>/<id>/download`
   - 支持下载归档日志或闪回日志

权限规则：

1. 首期全部使用 `@admin_required`
2. 如后续开放普通用户，再复用 `AccessControlService.ensure_connection_access`

### 7.4 统一日志聚合设计

保留现有 `ExecutionLog` 表不动，统一日志页采用“聚合返回”方式：

1. 归档日志来源：
   - 继续使用现有 `ExecutionLog`
2. 闪回日志来源：
   - 直接读取 `FlashbackTask`
   - 将其映射为统一日志结构

统一日志结构建议字段：

1. `log_type`
2. `id`
3. `task_id`
4. `task_name`
5. `status`
6. `start_time`
7. `end_time`
8. `log_file`
9. `error_message`
10. `detail_path`

映射规则：

1. 归档日志：
   - `log_type = archive`
   - `id = execution_log.id`
   - `task_name = archive_task.task_name`
2. 闪回日志：
   - `log_type = flashback`
   - `id = flashback_task.id`
   - `task_name = {database_name}.{table_name}`
   - `start_time = started_at`
   - `end_time = finished_at`
   - `log_file = log_file`
   - `error_message = error_message`
   - `detail_path = /flashback-tasks/{id}`

## 8. 校验与异常处理

### 8.1 前后端共同校验

1. 数据库连接必填
2. 数据库名必填
3. 表名必填
4. SQL 类型必填
5. 输出类型必填

### 8.2 时间与文件边界校验

1. `start_datetime` 和 `stop_datetime` 可都为空
2. `start_datetime`、`stop_datetime` 若同时存在，必须满足开始时间不晚于结束时间
3. `start_file` 和 `stop_file` 可都为空
4. `start_file`、`stop_file` 支持单独填写，命令构建时仅拼接非空参数
5. 第一版允许“仅时间范围”或“仅文件范围”或“两者都填”

### 8.3 执行与结果异常

1. `/my2sql` 不存在或不可执行时，任务立即失败
2. 数据库连接无效时，任务失败并记录错误
3. 子进程非零退出码时，任务失败
4. 子进程成功但结果文件缺失时，任务失败
5. 日志读取失败时，仅日志查看接口报错，不影响已完成任务状态

## 9. 安全与审计

1. 前端永不返回数据库密码
2. 后端日志与数据库中永不保存明文密码
3. `masked_command` 中将 `-password` 参数值替换为 `******`
4. 下载接口需再次校验任务存在性与访问权限
5. 任务产物目录按任务隔离，避免跨任务串读
6. 详情页展示连接名称与 `host:port`，不展示用户名与密码

## 10. 测试策略

### 后端测试

1. 参数校验测试
2. 命令构建测试
3. 可选参数省略测试
4. 密码脱敏测试
5. 任务状态流转测试
6. 结果文件识别测试
7. 日志下载与结果文件下载测试
8. 权限校验测试

### 前端测试

1. 列表页筛选与跳转测试
2. 创建页表单校验测试
3. 连接切换后自动填充摘要测试
4. 详情页文件列表展示测试
5. 日志查看与下载按钮展示测试
6. 状态标签展示测试
7. 执行日志页的归档/闪回统一展示测试
8. 执行日志页按日志类型筛选测试

### 回归验证

1. `npm test`
2. 后端对应单测
3. 手工验证 `/my2sql` 真机环境执行

## 11. 计划涉及的主要文件

后端：

1. `backend/app.py`
2. `backend/models/__init__.py`
3. `backend/models/flashback_task.py`（新增）
4. `backend/services/flashback_service.py`（新增）
5. `backend/tests/*flashback*`（新增）

前端：

1. `frontend/src/router/index.ts`
2. `frontend/src/auth/access.ts`
3. `frontend/src/components/Layout/Sidebar.vue`
4. `frontend/src/types/index.ts`
5. `frontend/src/api/flashbackTask.ts`（新增）
6. `frontend/src/stores/flashbackTask.ts`（新增）
7. `frontend/src/api/executionLog.ts`
8. `frontend/src/stores/executionLog.ts`
9. `frontend/src/views/ExecutionLogList.vue`
10. `frontend/src/views/FlashbackTaskList.vue`（新增）
11. `frontend/src/views/FlashbackTaskCreate.vue`（新增）
12. `frontend/src/views/FlashbackTaskDetail.vue`（新增）
13. `frontend/src/views/*.spec.ts`（新增或更新）

## 12. 交付标准

1. 管理员可创建一次性数据闪回生成任务。
2. 后台正确调用 `/my2sql` 并记录日志。
3. 任务详情中可查看日志、下载日志。
4. 任务详情中可下载 3 个结果文件：
   - `binlog_status.txt`
   - `biglong_trx.txt`
   - `*.sql`
5. 密码不在前端、日志、数据库命令展示中明文出现。
6. 页面风格与当前系统现有紧凑 UI 风格一致。
