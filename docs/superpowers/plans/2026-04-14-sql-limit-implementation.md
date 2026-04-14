# SQL 限流首期闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有平台中交付 SQL 限流首期闭环（规则管理、立即执行、后台调度、采样分析、KILL QUERY、运行留痕、执行日志联动）。

**Architecture:** 基于 Flask 单体后端扩展模型与服务，按“规则配置 -> 采样聚合 -> 命中判断 -> 安全过滤 -> KILL -> 审计留痕”执行链路实现。复用现有 APScheduler 与执行日志聚合能力，并在前端新增 SQL 限流规则/运行页面，保持当前风格与权限模型一致。

**Tech Stack:** Flask, Flask-SQLAlchemy, APScheduler, PyMySQL, Vue3, Pinia, Element Plus, Vitest, unittest

---

### Task 1: 后端数据模型与指纹能力

**Files:**
- Create: `backend/models/sql_throttle_rule.py`
- Create: `backend/models/sql_throttle_run.py`
- Create: `backend/models/sql_throttle_kill_log.py`
- Create: `backend/models/sql_throttle_fingerprint_state.py`
- Create: `backend/services/sql_fingerprint_service.py`
- Modify: `backend/models/__init__.py`

- [ ] 定义 4 张核心表模型与 `to_dict()` 输出
- [ ] 实现 SQL 指纹归一化（注释/空白/常量替换）与哈希能力
- [ ] 运行模型相关测试，确保 SQLite 测试环境可建表

### Task 2: 采样执行链路与调度服务

**Files:**
- Create: `backend/services/mysql_session_collector.py`
- Create: `backend/services/sql_throttle_executor_service.py`
- Create: `backend/services/sql_throttle_rule_service.py`
- Create: `backend/services/sql_throttle_scheduler_service.py`
- Modify: `backend/services/scheduler_service.py`（仅必要时复用调度器实例）

- [ ] 实现 MySQL 会话采样（performance_schema 优先，processlist fallback）
- [ ] 实现规则执行器（命中判断、连续命中、排序、白名单、安全过滤、dry-run、KILL QUERY）
- [ ] 实现规则 CRUD/启停/立即执行服务
- [ ] 实现 SQL 限流调度器初始化与周期执行

### Task 3: API 与执行日志集成

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/services/execution_log_service.py`

- [ ] 增加 SQL 限流规则与运行记录 API
- [ ] 增加 `/api/sql-throttle-rules/<id>/run-once`
- [ ] 扩展执行日志 `log_type` 支持 `sql_throttle_run` / `sql_kill` / `all`
- [ ] 兼容结构化日志内容读取接口

### Task 4: 前端接入与页面

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/auth/access.ts`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/sqlThrottle.ts`
- Create: `frontend/src/stores/sqlThrottle.ts`
- Create: `frontend/src/views/SqlThrottleRuleList.vue`
- Create: `frontend/src/views/SqlThrottleRunList.vue`
- Create: `frontend/src/views/SqlThrottleRunDetail.vue`
- Modify: `frontend/src/api/executionLog.ts`
- Modify: `frontend/src/stores/executionLog.ts`
- Modify: `frontend/src/views/ExecutionLogList.vue`

- [ ] 新增 SQL 限流菜单与路由
- [ ] 新增规则列表（含启停、删除、立即执行）与规则弹窗编辑
- [ ] 新增运行记录列表/详情与 Kill 明细展示
- [ ] 执行日志页增加 SQL 限流日志类型筛选

### Task 5: 测试与验证

**Files:**
- Create: `backend/tests/test_sql_throttle_api.py`
- Modify: `backend/tests/test_execution_log_api.py`
- Create/Modify: `frontend/src/views/SqlThrottle*.spec.ts`
- Modify: `frontend/src/views/ExecutionLogList.spec.ts`

- [ ] 规则参数校验、run once、dry-run、连续命中、Kill 结果测试
- [ ] 执行日志 SQL 限流聚合查询测试
- [ ] 前端关键交互与筛选行为测试
- [ ] 运行后端与前端测试命令并记录结果
