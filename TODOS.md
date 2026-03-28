# 项目待办事项

## 📋 概述
本文档记录数据库运维管理平台的待办事项、改进计划和功能扩展。

---

## 🎯 优先级 P1（立即执行）

### 1. 增强 SQL 优化功能 - 添加 SQL 可视化和执行计划展示
- **状态**: 已添加到计划
- **优先级**: P1
- **描述**: 在 SQL 优化建议页面添加执行计划的可视化展示、SQL 格式化、索引推荐显示
- **关联**: CEO Review 接受的扩展
- **预计工作量**: M（约 2-3 小时）

---

## 🔒 优先级 P2（近期计划）

### 2. 用户认证与权限系统
- **状态**: 推迟到 TODOS.md
- **优先级**: P2
- **描述**: 添加用户登录、角色权限管理、操作日志记录
- **关联**: CEO Review 推迟项
- **预计工作量**: L（约 1 天）
- **依赖**: 无

### 3. 完整的测试套件
- **状态**: 推迟到 TODOS.md
- **优先级**: P2
- **描述**: 添加后端单元测试、前端测试、集成测试
- **关联**: CEO Review 推迟项
- **预计工作量**: L（约 1-2 天）
- **依赖**: 无

### 4. Docker 支持和 CI/CD 流水线
- **状态**: 已完成
- **优先级**: P2
- **描述**: 添加 Dockerfile、docker-compose、GitHub Actions/GitLab CI 配置
- **关联**: CEO Review 推迟项
- **预计工作量**: M（约 3-4 小时）
- **依赖**: 无
- **文件**: Dockerfile.backend、Dockerfile.frontend、docker-compose.yml、nginx.conf、.github/workflows/ci.yml、.gitlab-ci.yml

---

## ⚙️ 优先级 P3（技术债务/优化）

### 5. 代码重构和架构优化
- **状态**: 待处理
- **优先级**: P3
- **描述**:
  - 使用 Flask Blueprints 重构路由
  - 优化错误处理和异常捕获
  - 添加更完善的日志系统

---

## ✅ 已完成

### 2026-03-26
- ✅ 复杂 SQL 表名提取的完美解决方案（混合 LLM 解析策略）
- ✅ 延长 API 调用超时时间（从 30/60 秒到 120 秒）
- ✅ 修复循环导入问题（延迟导入 LLMService）
- ✅ 支持 qwen3-max 模型调用（更新 SQL 优化和解析模型）

---

## 📝 备注

### 关于模型调用
当前的 API 调用方式使用的是阿里云 DashScope 的通用文本生成接口：
- API URL: `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- 当前使用模型:
  - SQL 优化: `qwen3-max`
  - SQL 解析: `qwen3-max`

### 架构改进建议
- 考虑使用 Flask Blueprints 模块化路由
- 添加更完善的配置管理系统
- 考虑使用异步任务处理（如 Celery）来处理耗时的 LLM 调用
