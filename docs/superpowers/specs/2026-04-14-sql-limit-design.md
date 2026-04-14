# SQL 限流功能设计说明书

## 1. 背景与目标

当前数据库运维平台已具备数据库连接管理、慢 SQL 管理、执行日志等基础能力，但缺少在数据库出现慢 SQL 堵塞、同类 SQL 高并发堆积、CPU 飙高时进行自动识别与限流处置的能力。

本次新增的 **SQL 限流功能**，目标是在现有平台中支持对 MySQL 5.7 与 MySQL 8.0 数据库进行周期性会话采集、SQL 指纹聚合、规则命中判断、自动 Kill、处置留痕与人工复盘，降低慢 SQL 突发堆积对实例可用性的影响。

### 目标

1. 支持基于已添加数据库连接创建 SQL 限流规则。
2. 支持对 MySQL 5.7、MySQL 8.0 实例进行周期性会话采集与分析。
3. 支持配置慢 SQL 阈值、同指纹并发阈值、采集周期、单轮最大 Kill 数等规则。
4. 支持提取 SQL 指纹，对当前活跃会话按指纹进行实时聚合。
5. 当命中限流规则时，优先 Kill 同指纹重复数最多的 SQL。
6. 支持记录每次命中的采样快照、命中规则、Kill 明细、执行结果与错误信息。
7. 支持规则启停、任务后台定时执行、处置日志查看、手工复盘。
8. 页面风格与现有系统保持一致，便于 superpowers 下一步直接开发。

### 非目标

1. 本期不做 SQL 改写、排队、熔断网关、连接池代理层限流。
2. 本期不支持 PostgreSQL、Oracle、SQL Server 等其他数据库。
3. 本期不做跨实例联动处置。
4. 本期不做 AI 根因分析，只做规则驱动的检测与自动 Kill。
5. 本期不接入审批流，但保留后续扩展点。

## 2. 设计原则

1. **安全优先**：默认只 Kill 命中规则且满足安全条件的 SQL，不 Kill 系统线程、复制线程、平台自身连接与白名单连接。
2. **最小侵入**：优先使用 MySQL 系统视图与 performance_schema 获取会话信息，不要求在业务侧改 SQL。
3. **兼容 5.7 / 8.0**：同一套规则模型适配 MySQL 5.7、8.0，采集 SQL 做版本分支处理。
4. **幂等可追溯**：每次调度执行、每次命中分析、每次 Kill 都要可审计、可回放、可复盘。
5. **逐级收敛**：优先 Kill 重复数最高、执行时间最长、影响面最大的同类 SQL，避免一次性误杀过多线程。

## 3. 术语定义

### 3.1 SQL 指纹

将原始 SQL 进行标准化处理后得到的归一化标识。标准化原则建议如下：

1. 去除多余空白与注释。
2. 统一关键字大小写。
3. 将常量值替换为占位符，如数字、字符串、IN 列表中的值。
4. 统一 LIMIT 常量、比较值、日期值。
5. 保留表名、操作类型、谓词结构、排序与分组结构。

示例：

```sql
select * from orders where user_id = 1001 and status = 'paid'
select * from orders where user_id = 1002 and status = 'paid'
```

归一化后可统一为：

```sql
SELECT * FROM orders WHERE user_id = ? AND status = ?
```

### 3.2 慢 SQL

在本功能中，慢 SQL 不是以慢日志文件为唯一依据，而是指 **当前正在执行且已运行时间超过规则阈值的活跃 SQL**。

### 3.3 同指纹并发数

在单次采样中，同一 SQL 指纹下、同时处于活跃执行状态的会话数量。

## 4. 方案概览

推荐采用 **规则配置 + 后台调度 + 实时采样分析 + 自动处置 + 审计留痕** 的方案。

### 4.1 整体流程

1. 管理员在平台中选择数据库连接并创建限流规则。
2. 规则启用后，由后台调度器按设定周期执行采样任务。
3. 采样任务连接目标 MySQL，实时拉取当前活跃会话。
4. 对活跃会话提取 SQL 文本、执行时间、用户、来源、DB、线程 ID 等信息。
5. 对 SQL 进行指纹归一化并按指纹聚合。
6. 若某指纹命中慢 SQL 阈值与并发阈值，则进入候选处置集合。
7. 在候选集合中，优先选出重复数最多的指纹；若并列，则按最长运行时间、最大总运行时长排序。
8. 对候选指纹下的线程执行安全过滤。
9. 按规则执行 Kill，并记录处置批次、线程清单、Kill 结果与失败原因。
10. 前端支持查看规则、当前状态、命中历史、Kill 日志与样本 SQL。

### 4.2 建议的采集来源

**结论：优先使用 performance_schema / information_schema 系统视图，processlist 作为兼容兜底，不建议仅依赖 `SHOW PROCESSLIST`。**

原因如下：

1. `SHOW PROCESSLIST` 信息有限，不利于稳定程序化采集。
2. `INFORMATION_SCHEMA.PROCESSLIST` 适合做基础兼容，但 SQL 文本、阶段信息、扩展字段有限。
3. `performance_schema` 在 5.7、8.0 中都可用于获取更结构化的线程、当前语句、执行时间等信息。
4. 自动 Kill 场景需要更可控的过滤条件和更稳定的字段来源。

### 4.3 采集优先级

建议采用以下优先级：

1. **首选：performance_schema.threads + performance_schema.events_statements_current**
2. **备选：information_schema.processlist**
3. **兜底：SHOW FULL PROCESSLIST**

### 4.4 推荐实现策略

后端对不同版本自动探测并选择采集 SQL：

1. 连接成功后识别实例版本、`performance_schema` 是否开启。
2. 若 `performance_schema` 可用，则走增强采集路径。
3. 若不可用或权限不足，则回退到 `information_schema.processlist`。
4. 若仍失败，则标记本轮采样失败并记录原因。

## 5. 功能范围

### 5.1 规则管理

支持管理员创建、编辑、启停、删除 SQL 限流规则。

每条规则绑定一个数据库连接，一条规则只作用于一个实例。

### 5.2 自动调度

规则启用后自动加入后台定时任务，由平台统一调度执行。

### 5.3 实时分析

对目标实例当前活跃会话进行采样与聚合，识别高重复慢 SQL。

### 5.4 自动处置

当命中规则时，自动 Kill 命中指纹下的会话，优先处置重复数最多的指纹。

### 5.5 审计与复盘

记录采样快照、命中原因、候选列表、实际 Kill 清单、返回结果、异常信息。

## 6. 规则模型设计

新增实体：`SqlThrottleRule`

建议字段如下：

1. `id`
2. `rule_name`
3. `db_connection_id`
4. `connection_name`
5. `mysql_version`
6. `enabled`
7. `slow_sql_seconds`
8. `fingerprint_concurrency_threshold`
9. `poll_interval_seconds`
10. `max_kill_per_round`
11. `min_rows_examined`（预留）
12. `target_db_pattern`（可空）
13. `target_user_pattern`（可空）
14. `exclude_users`
15. `exclude_hosts`
16. `exclude_dbs`
17. `exclude_fingerprints`
18. `dry_run`
19. `kill_command`
20. `kill_scope`
21. `kill_order`
22. `consecutive_hit_times`
23. `status`
24. `last_run_at`
25. `last_hit_at`
26. `last_error_message`
27. `creator_user_id`
28. `created_at`
29. `updated_at`

### 6.1 核心字段说明

1. `slow_sql_seconds`：慢 SQL 判定阈值，单位秒，例如 10。
2. `fingerprint_concurrency_threshold`：同指纹并发阈值，例如 20。
3. `poll_interval_seconds`：采样周期，建议默认 15 秒。
4. `max_kill_per_round`：单轮最多 Kill 线程数，防止过度处置，建议默认 10。
5. `dry_run`：只分析不 Kill，用于灰度验证。
6. `kill_command`：默认 `KILL QUERY`，首期不建议直接 `KILL CONNECTION`。
7. `kill_scope`：默认 `same_fingerprint_only`。
8. `kill_order`：默认 `dup_count_desc_exec_time_desc`。
9. `consecutive_hit_times`：连续命中多少轮才触发，建议默认 1，生产建议可配为 2 或 3。

### 6.2 推荐默认值

1. `slow_sql_seconds = 10`
2. `fingerprint_concurrency_threshold = 20`
3. `poll_interval_seconds = 15`
4. `max_kill_per_round = 10`
5. `dry_run = true`（新建规则首次建议默认演练模式）
6. `kill_command = KILL QUERY`
7. `consecutive_hit_times = 2`

### 6.3 首期确认项

根据业务确认，首期按以下约束实现：

1. **Kill 方式固定为 `KILL QUERY`**，首期不支持 `KILL CONNECTION`。
2. **触发条件不引入 CPU 指标**，仅基于“慢 SQL 阈值 + 同指纹并发阈值”判断。
3. **采样周期默认值固定为 15 秒**。
4. **支持“立即执行一次”按钮**，用于规则灰度验证与联调。
5. **启用系统默认白名单机制**，默认排除平台自身连接、复制账号、备份账号、监控账号等。

## 7. 采样与分析设计

## 7.1 采样目标

仅采集当前活跃、与业务 SQL 相关、且满足最小运行时长条件的会话。

### 7.2 建议过滤条件

过滤掉以下线程：

1. 当前命令不是 Query / Execute 的线程。
2. `Sleep`、`Binlog Dump`、`Replica`、`Connect` 等非目标线程。
3. 平台自身采集连接。
4. 系统账号、复制账号、监控账号。
5. SQL 文本为空的线程。
6. 已在执行 Kill 的线程。

### 7.3 兼容版采样字段

不论底层来源为何，采样后统一映射成以下结构：

```json
{
  "thread_id": 12345,
  "process_id": 12345,
  "user": "app_user",
  "host": "10.10.10.5:49321",
  "db": "order_db",
  "command": "Query",
  "state": "Sending data",
  "exec_time_seconds": 18,
  "sql_text": "select * from orders where user_id = 1001 and status = 'paid'",
  "fingerprint": "SELECT * FROM orders WHERE user_id = ? AND status = ?",
  "digest": "optional",
  "sample_time": "2026-04-14T08:00:00"
}
```

### 7.4 候选识别逻辑

单次采样后，按 `fingerprint` 分组，计算：

1. `concurrency_count`
2. `max_exec_time`
3. `avg_exec_time`
4. `sum_exec_time`
5. `sample_sql_text`
6. `thread_ids`

命中条件建议为：

1. `concurrency_count >= fingerprint_concurrency_threshold`
2. 且该组内至少有一条 SQL 满足 `exec_time_seconds >= slow_sql_seconds`

更稳妥的增强版条件可选：

1. `concurrency_count >= threshold`
2. 且组内全部线程都超过阈值，或超过阈值的线程数占比超过设定比例

首期建议采用简化版条件，便于快速落地。

### 7.5 触发优先级

若单轮有多个指纹同时命中，则按以下顺序选择：

1. `concurrency_count` 降序
2. `max_exec_time` 降序
3. `sum_exec_time` 降序
4. `fingerprint` 字典序

### 7.6 连续命中控制

为了避免瞬时抖动触发误杀，建议支持连续命中计数：

1. 指纹本轮命中则计数 +1。
2. 指纹本轮未命中则计数清零。
3. 当计数达到 `consecutive_hit_times` 后才允许自动 Kill。

首期可以按 **规则维度** 做连续命中，也可以按 **指纹维度** 做连续命中。推荐按指纹维度实现，更准确。

## 8. Kill 处置策略

### 8.1 处置原则

1. 默认只 Kill 命中指纹下的 SQL。
2. 优先 Kill 同指纹组内运行时间最长的线程。
3. 每轮处置数量不超过 `max_kill_per_round`。
4. 建议优先使用 `KILL QUERY`，避免直接断开连接带来更大影响。

### 8.2 Kill 排序

命中指纹组内线程按以下顺序排序后执行 Kill：

1. `exec_time_seconds` 降序
2. `thread_id` 升序

### 8.3 安全白名单

必须排除以下对象：

1. 平台自身连接。
2. 管理账号。
3. 复制账号。
4. 备份账号。
5. 监控账号。
6. 显式白名单用户。
7. 显式白名单 DB。
8. 显式白名单指纹。
9. 显式白名单主机。

### 8.4 Kill 执行结果分类

1. `success`
2. `already_finished`
3. `permission_denied`
4. `thread_not_found`
5. `failed`

## 9. 后台调度设计

推荐采用 **规则调度器 + 执行器** 模式：

1. 调度器周期扫描启用规则。
2. 满足执行时间窗口的规则生成一次调度任务。
3. 执行器串行或有限并发执行采样分析。
4. 每次执行形成一条运行记录。

### 9.1 调度要求

1. 同一规则在同一时刻只能有一个运行实例，避免重复采样。
2. 若上一轮未结束，下一轮跳过并记录 `skipped`。
3. 支持服务重启后自动恢复调度。

### 9.2 建议实现

若当前平台已有后台线程任务模型，可复用；若无，则建议新增：

1. `SqlThrottleSchedulerService`
2. `SqlThrottleExecutorService`

## 10. 数据模型设计

除 `SqlThrottleRule` 外，建议新增以下表。

### 10.1 规则运行表：`sql_throttle_run`

记录每一轮调度执行。

建议字段：

1. `id`
2. `rule_id`
3. `status`（queued / running / completed / failed / skipped）
4. `sample_started_at`
5. `sample_finished_at`
6. `total_session_count`
7. `candidate_fingerprint_count`
8. `hit_fingerprint_count`
9. `kill_attempt_count`
10. `kill_success_count`
11. `dry_run`
12. `error_message`
13. `snapshot_json`
14. `created_at`
15. `updated_at`

`snapshot_json` 用于存储本轮采样后的聚合快照，可用于详情页复盘。

### 10.2 Kill 明细表：`sql_throttle_kill_log`

记录每个线程的处置结果。

建议字段：

1. `id`
2. `run_id`
3. `rule_id`
4. `thread_id`
5. `db_user`
6. `db_host`
7. `db_name`
8. `fingerprint`
9. `sample_sql_text`
10. `exec_time_seconds`
11. `kill_command`
12. `kill_result`
13. `kill_error_message`
14. `killed_at`
15. `created_at`

### 10.3 指纹命中状态表：`sql_throttle_fingerprint_state`

用于连续命中计数。

建议字段：

1. `id`
2. `rule_id`
3. `fingerprint_hash`
4. `fingerprint`
5. `consecutive_hit_count`
6. `last_seen_at`
7. `last_hit_at`
8. `created_at`
9. `updated_at`

## 11. 页面与信息架构设计

## 11.1 导航建议

左侧导航建议采用以下方式：

1. 一级菜单：`SQL 限流`
2. 二级菜单：规则管理 / 运行记录
3. `执行日志` 继续沿用现有菜单入口

说明：

1. **Kill 日志不新增独立菜单**。
2. **Kill 记录并入现有“执行日志”功能中展示**。
3. `执行日志` 页面增加日志类型筛选，支持查看 SQL 限流相关日志。

### 11.2 SQL 限流规则列表页

用途：展示规则、启停规则、进入创建页、查看最近状态。

字段建议：

1. 规则 ID
2. 规则名称
3. 连接名称
4. MySQL 版本
5. 慢 SQL 阈值
6. 并发阈值
7. 采样周期
8. 单轮最大 Kill 数
9. 是否演练模式
10. 状态
11. 最近执行时间
12. 最近命中时间
13. 操作

操作项：

1. 查看详情
2. 编辑
3. 启用
4. 停用
5. 删除
6. 立即执行一次（可选）

### 11.3 创建 / 编辑规则页

表单字段建议：

1. 数据库连接：下拉选择
2. 规则名称：必填
3. 慢 SQL 阈值秒数：必填
4. 同指纹并发阈值：必填
5. 采样周期秒数：必填
6. 单轮最大 Kill 数：必填
7. 连续命中次数：必填
8. Kill 方式：固定展示 `KILL QUERY`
9. 是否演练模式：开关
10. 排除用户：可选，多值
11. 排除 DB：可选，多值
12. 排除主机：可选，多值
13. 排除指纹：可选，多值
14. 启用状态：开关

页面说明区建议展示：

1. 当前连接的 `host:port`
2. MySQL 版本
3. 采集模式（performance_schema / processlist fallback）

### 11.4 运行记录列表页

用途：查看每轮调度执行结果。

字段建议：

1. 运行 ID
2. 规则名称
3. 连接名称
4. 执行状态
5. 采样时间
6. 活跃会话数
7. 候选指纹数
8. 命中指纹数
9. Kill 尝试数
10. Kill 成功数
11. 是否演练模式
12. 错误信息
13. 操作

操作项：

1. 查看详情
2. 查看执行日志

### 11.5 运行详情页

页面结构建议：

1. 运行摘要卡片
2. 命中指纹卡片
3. 候选指纹排行卡片
4. Kill 明细卡片
5. 原始采样快照卡片
6. 调试日志卡片

### 11.6 执行日志页集成说明

Kill 日志复用现有“执行日志”页面统一展示，不新增独立 Kill 日志页。

页面改造建议：

1. 增加 `日志类型` 筛选：全部 / 归档日志 / 闪回日志 / SQL 限流日志 / SQL Kill 日志。
2. SQL 限流运行日志按“运行批次”维度展示。
3. SQL Kill 日志按“线程处置明细”维度展示。
4. 点击日志记录可跳转到对应 SQL 限流运行详情页。
5. 对 Kill 日志，列表中需展示规则名称、连接名称、线程 ID、DB、执行时长、指纹摘要、Kill 结果、Kill 时间。


其中：

1. `SQL 限流运行日志` 来源于 `sql_throttle_run`
2. `SQL Kill 日志` 来源于 `sql_throttle_kill_log`

## 12. API 设计

建议新增接口如下：

### 12.1 规则管理接口

1. `GET /api/sql-throttle-rules`
2. `POST /api/sql-throttle-rules`
3. `GET /api/sql-throttle-rules/<id>`
4. `PUT /api/sql-throttle-rules/<id>`
5. `POST /api/sql-throttle-rules/<id>/enable`
6. `POST /api/sql-throttle-rules/<id>/disable`
7. `DELETE /api/sql-throttle-rules/<id>`
8. `POST /api/sql-throttle-rules/<id>/run-once`

### 12.2 运行记录接口

1. `GET /api/sql-throttle-runs`
2. `GET /api/sql-throttle-runs/<id>`
3. `GET /api/sql-throttle-runs/<id>/kill-logs`
4. `GET /api/sql-throttle-runs/<id>/snapshot`

### 12.3 执行日志集成接口

Kill 日志并入现有执行日志功能，建议调整现有执行日志接口，使其支持展示 SQL 限流相关日志。

建议接口如下：

1. `GET /api/execution-logs`

   * 新增 `log_type` 参数：`archive` / `flashback` / `sql_throttle_run` / `sql_kill` / 空
2. `GET /api/execution-logs/<type>/<id>`

   * 读取统一日志详情
3. `GET /api/execution-logs/<type>/<id>/content`

   * 读取日志内容或日志摘要

说明：

1. `sql_throttle_run` 日志来源于 `sql_throttle_run`
2. `sql_kill` 日志来源于 `sql_throttle_kill_log`
3. 若当前现有执行日志页面仅支持文件型日志，也可对 Kill 日志做“结构化日志适配显示”，无需强制落地为单独日志文件

## 13. 后端架构建议

### 13.1 模型层

新增：

1. `backend/models/sql_throttle_rule.py`
2. `backend/models/sql_throttle_run.py`
3. `backend/models/sql_throttle_kill_log.py`
4. `backend/models/sql_throttle_fingerprint_state.py`

调整：

1. 复用并扩展现有执行日志聚合查询逻辑，使其支持 `sql_throttle_run` 与 `sql_kill` 两类日志来源

### 13.2 服务层

新增：

1. `backend/services/sql_throttle_rule_service.py`
2. `backend/services/sql_throttle_scheduler_service.py`
3. `backend/services/sql_throttle_executor_service.py`
4. `backend/services/sql_fingerprint_service.py`
5. `backend/services/mysql_session_collector.py`

调整：

1. `backend/services/execution_log_service.py`（或现有统一日志服务）

   * 增加 SQL 限流运行日志与 SQL Kill 日志的聚合适配能力

### 13.3 关键职责划分

`mysql_session_collector.py`：

1. 识别 MySQL 版本与能力。
2. 采集活跃会话。
3. 统一返回会话结构。

`sql_fingerprint_service.py`：

1. SQL 清洗。
2. SQL 归一化。
3. 指纹生成。
4. 指纹哈希。

`sql_throttle_executor_service.py`：

1. 单轮规则执行。
2. 指纹聚合。
3. 命中判断。
4. Kill 决策。
5. Kill 执行。
6. 运行记录与日志落库。

## 14. 核心执行流程

### 14.1 创建规则

1. 管理员选择已添加数据库连接。
2. 配置限流阈值与安全参数。
3. 保存后规则进入启用或停用状态。

### 14.2 定时执行

1. 调度器扫描启用规则。
2. 判断是否达到 `poll_interval_seconds`。
3. 为规则创建一条 `run` 记录。
4. 执行器开始采样。

### 14.3 采样分析

1. 拉取活跃会话。
2. 清理无效线程。
3. 生成指纹。
4. 按指纹聚合。
5. 识别命中组。
6. 计算是否达到连续命中阈值。

### 14.4 自动 Kill

1. 选出优先处置指纹。
2. 过滤白名单线程。
3. 生成 Kill 列表。
4. 逐条执行 `KILL QUERY <thread_id>`。
5. 写入 Kill 明细表。

### 14.5 完成与留痕

1. 更新运行记录状态。
2. 记录命中摘要与错误信息。
3. 前端可查看明细与复盘快照。

## 15. 关键 SQL 采集建议

### 15.1 MySQL 8.0 / 5.7 增强路径

优先从 performance_schema 获取当前语句与线程信息，再映射为统一结构。

建议实现为后端内置 SQL 模板，而不是前端拼接。

### 15.2 fallback 路径

当 performance_schema 不可用时，查询 `information_schema.processlist` 获取：

1. `ID`
2. `USER`
3. `HOST`
4. `DB`
5. `COMMAND`
6. `TIME`
7. `STATE`
8. `INFO`

并基于 `TIME` + `INFO` 做基础分析。

### 15.3 为什么不建议只靠 processlist

1. 字段语义较粗。
2. 复杂场景下 SQL 文本可能不完整。
3. 难以做后续增强能力，如 digest、阶段分析、更多性能标签。

## 16. 校验与异常处理

### 16.1 前后端共同校验

1. 数据库连接必填。
2. 规则名称必填。
3. 慢 SQL 阈值必须大于 0。
4. 并发阈值必须大于 1。
5. 采样周期必须大于等于 5 秒。
6. 单轮最大 Kill 数必须大于 0。
7. 连续命中次数必须大于等于 1。

### 16.2 执行异常

1. 连接失败：本轮 `failed`。
2. 权限不足：本轮 `failed`，并在规则上显示最近错误。
3. 采样 SQL 执行失败：本轮 `failed`。
4. Kill 失败：记录到线程级明细，不影响整轮记录落库。
5. 本轮无命中：状态 `completed`，Kill 数为 0。

## 17. 安全设计

1. 自动 Kill 默认关闭，规则首次创建建议默认 `dry_run = true`。
2. 默认仅管理员可创建和启停规则。
3. 连接密码不回传前端。
4. 平台审计日志中不记录明文密码。
5. 规则删除不删除历史运行记录与 Kill 日志。
6. 禁止 Kill 平台自身采集线程。
7. 首期默认只开放 `KILL QUERY`。

## 18. 测试策略

### 18.1 后端测试

1. 规则参数校验测试。
2. 版本识别与采集路径选择测试。
3. SQL 指纹归一化测试。
4. 指纹聚合测试。
5. 命中判断测试。
6. 连续命中计数测试。
7. Kill 排序测试。
8. 安全白名单过滤测试。
9. Dry-run 测试。
10. Kill 日志落库测试。

### 18.2 前端测试

1. 规则列表展示与筛选测试。
2. 创建页表单校验测试。
3. 规则启停测试。
4. 运行记录详情查看测试。
5. Kill 日志筛选测试。

### 18.3 联调验证

准备以下场景：

1. 同指纹 5 条，不达阈值，不触发。
2. 同指纹 20 条，执行时间都超过阈值，触发。
3. 同时有两个指纹命中，验证优先级。
4. 命中线程中包含白名单用户，验证不会被 Kill。
5. Dry-run 命中，验证只记录不执行。
6. performance_schema 不可用，验证自动回退。

## 19. 计划涉及的主要文件

后端：

1. `backend/models/sql_throttle_rule.py`
2. `backend/models/sql_throttle_run.py`
3. `backend/models/sql_throttle_kill_log.py`
4. `backend/models/sql_throttle_fingerprint_state.py`
5. `backend/services/mysql_session_collector.py`
6. `backend/services/sql_fingerprint_service.py`
7. `backend/services/sql_throttle_rule_service.py`
8. `backend/services/sql_throttle_scheduler_service.py`
9. `backend/services/sql_throttle_executor_service.py`
10. `backend/api/sql_throttle.py`
11. `backend/services/execution_log_service.py`（或现有执行日志聚合服务，需改造）
12. `backend/tests/*sql_throttle*`

前端：

1. `frontend/src/router/index.ts`
2. `frontend/src/types/index.ts`
3. `frontend/src/api/sqlThrottle.ts`
4. `frontend/src/stores/sqlThrottle.ts`
5. `frontend/src/api/executionLog.ts`（需扩展 SQL 限流 / Kill 日志筛选）
6. `frontend/src/stores/executionLog.ts`（需扩展统一日志展示）
7. `frontend/src/views/SqlThrottleRuleList.vue`
8. `frontend/src/views/SqlThrottleRuleForm.vue`
9. `frontend/src/views/SqlThrottleRunList.vue`
10. `frontend/src/views/SqlThrottleRunDetail.vue`
11. `frontend/src/views/ExecutionLogList.vue`（需改造）

## 20. 交付标准

1. 管理员可基于已添加数据库连接创建 SQL 限流规则。
2. 规则可加入后台定时调度并按周期执行。
3. 平台可采集 MySQL 5.7 / 8.0 当前活跃会话。
4. 平台可生成 SQL 指纹并按指纹聚合并发数。
5. 命中规则后可优先 Kill 指纹重复数最多的 SQL。
6. 每次运行、每次命中、每次 Kill 都有审计记录。
7. 前端可查看规则、运行记录，并在现有“执行日志”中查看 SQL 限流运行日志与 Kill 日志。
8. 支持 dry-run 演练模式。
9. 不会误 Kill 系统线程、复制线程、平台自身线程和白名单线程。

## 21. 已确认的首期范围

以下事项已经确认，可直接按此进入开发：

1. **Kill 方式固定为 `KILL QUERY`**。
2. **首期不引入 CPU 条件联动**。
3. **采样周期默认值为 15 秒**。
4. **支持“立即执行一次”按钮**。
5. **启用默认白名单机制**，至少包括复制账号、备份账号、监控账号、平台自身连接。

## 22. 推荐的首期落地范围

为确保 superpowers 下一步开发更稳，首期按以下闭环交付：

1. 规则管理
2. 定时调度
3. 基于 `performance_schema` / `processlist` 的活跃会话采样
4. SQL 指纹聚合
5. 命中后执行 `KILL QUERY`
6. 运行记录 + Kill 日志
7. dry-run 演练模式
8. 默认白名单过滤
9. 支持“立即执行一次”

这样首期可先把“检测-识别-处置-留痕”闭环跑通，后续再增加更细的白名单模板、统一日志中心、更复杂触发条件与更丰富安全策略。
