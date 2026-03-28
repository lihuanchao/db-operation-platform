# 数据库运维管理平台

## 项目概述

数据库运维管理平台是一个专为MySQL数据库优化设计的综合解决方案，提供慢SQL管理、执行计划分析、数据库连接管理和任务调度功能。

## 主要功能

### 1. 慢SQL管理
- **慢SQL列表与过滤**：支持按数据库、主机、时间范围和优化状态筛选
- **SQL优化建议**：集成阿里云通义千问LLM，提供智能SQL优化建议
- **执行计划分析**：可视化展示SQL执行计划，帮助定位性能瓶颈
- **批量优化**：支持批量处理多个慢SQL优化任务
- **报告下载**：提供Markdown格式的详细优化报告

### 2. 数据库连接管理
- **连接配置**：添加、编辑、删除数据库连接信息
- **连接测试**：验证连接的可用性
- **状态管理**：启用/禁用数据库连接
- **连接池管理**：优化连接资源使用

### 3. 任务调度与执行
- **归档任务**：执行数据归档操作
- **定时任务**：使用APScheduler实现复杂的定时任务调度
- **任务监控**：实时查看任务执行状态和日志
- **执行历史**：记录所有任务执行记录，支持查看和下载

### 4. 日志管理
- **执行日志**：实时显示任务执行日志
- **日志下载**：支持下载完整的执行日志
- **执行状态**：显示任务执行中、成功、失败状态

## 技术栈

### 后端
- **框架**：Flask 2.3+
- **ORM**：SQLAlchemy 2.0+
- **数据库**：MySQL (生产环境) / SQLite (开发环境)
- **定时任务**：APScheduler
- **AI集成**：阿里云通义千问API
- **密码加密**：Cryptography
- **报告生成**：Markdown生成与下载

### 前端
- **框架**：Vue 3 + TypeScript
- **构建工具**：Vite
- **UI组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP客户端**：Axios
- **图表**：ECharts (待集成)

### 部署与运维
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions / GitLab CI
- **反向代理**：Nginx
- **数据库**：MySQL 8.0+

## 项目结构

```
claude-project/
├── backend/                  # Flask后端
│   ├── app.py               # 主应用入口
│   ├── config.py            # 配置文件
│   ├── models/              # SQLAlchemy模型
│   │   ├── slow_sql.py      # 慢SQL模型
│   │   ├── db_connection.py # 数据库连接模型
│   │   ├── archive_task.py  # 归档任务模型
│   │   ├── cron_job.py      # 定时任务模型
│   │   └── execution_log.py # 执行日志模型
│   ├── services/            # 业务逻辑层
│   │   ├── llm_service.py   # LLM服务
│   │   ├── slow_sql_service.py # 慢SQL服务
│   │   ├── archive_service.py # 归档任务服务
│   │   ├── cron_service.py  # 定时任务服务
│   │   ├── scheduler_service.py # 调度器服务
│   │   ├── execution_log_service.py # 执行日志服务
│   │   ├── pt_archiver.py   # 数据归档工具
│   │   └── sql_metadata_service.py # SQL元数据服务
│   ├── utils/               # 工具函数
│   │   ├── downloader.py    # 报告下载功能
│   │   └── encryption.py    # 密码加密工具
│   ├── data/                # SQLite数据库
│   ├── production/          # 生产环境配置
│   └── requirements.txt     # Python依赖
├── frontend/                # Vue 3前端
│   ├── src/
│   │   ├── api/             # API接口
│   │   ├── components/      # Vue组件
│   │   ├── views/           # 页面视图
│   │   ├── stores/          # Pinia状态管理
│   │   ├── types/           # TypeScript类型定义
│   │   ├── router/          # 路由配置
│   │   └── main.ts          # 应用入口
│   ├── package.json         # 前端依赖
│   └── vite.config.ts       # Vite配置
├── docker-compose.yml       # Docker Compose配置
├── Dockerfile.backend       # 后端Docker镜像配置
├── Dockerfile.frontend      # 前端Docker镜像配置
├── nginx.conf               # Nginx配置
└── .github/workflows/ci.yml # GitHub Actions配置
```

## 快速开始

### 1. 环境准备
- Python 3.12+
- Node.js 20+
- Docker (推荐使用)
- MySQL 8.0+

### 2. Docker部署

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 本地开发

#### 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

#### 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 4. 环境变量配置

创建 `backend/.env` 文件：
```
# 数据库配置
DATABASE_URL=mysql://user:password@localhost:3306/dbname
# SQLite用于本地开发
# DATABASE_URL=sqlite:///data/app.db

# API密钥
DASHSCOPE_API_KEY=your_tongyi_qianwen_api_key

# 应用配置
FLASK_APP=app.py
FLASK_ENV=development
```

## API文档

### 慢SQL管理
- `GET /api/slow-sqls` - 获取慢SQL列表
- `POST /api/slow-sqls/optimize` - 优化SQL
- `POST /api/slow-sqls/batch-optimize` - 批量优化SQL

### 数据库连接
- `GET /api/connections` - 获取连接列表
- `POST /api/connections` - 创建连接
- `PUT /api/connections/<id>` - 更新连接
- `DELETE /api/connections/<id>` - 删除连接
- `POST /api/connections/<id>/test` - 测试连接

### 任务管理
- `GET /api/archive-tasks` - 获取归档任务列表
- `POST /api/archive-tasks` - 创建归档任务
- `POST /api/archive-tasks/execute` - 执行归档任务
- `GET /api/execution-logs` - 获取执行日志列表
- `GET /api/execution-logs/<id>` - 获取日志详情
- `GET /api/execution-logs/<id>/log-content` - 获取日志内容

### 定时任务
- `GET /api/cron-jobs` - 获取定时任务列表
- `POST /api/cron-jobs` - 创建定时任务
- `PUT /api/cron-jobs/<id>` - 更新定时任务
- `DELETE /api/cron-jobs/<id>` - 删除定时任务
- `PUT /api/cron-jobs/<id>/toggle` - 启用/禁用定时任务

## 功能使用说明

### 使用慢SQL优化功能

1. 确保已添加有效的数据库连接
2. 在慢SQL列表页面查看待优化的SQL
3. 点击"优化"按钮获取AI优化建议
4. 查看执行计划和优化建议
5. 下载详细的优化报告

### 创建定时任务

1. 进入定时任务管理页面
2. 点击"创建定时任务"
3. 配置任务参数：
   - 选择归档任务
   - 设置Cron表达式（支持秒级精度）
   - 配置执行策略
4. 保存并启用定时任务

### 查看执行日志

1. 在执行日志页面查看所有任务的执行记录
2. 点击"查看日志"查看实时执行状态
3. 点击"下载日志"保存完整的执行日志

## 开发与贡献

### 代码规范

#### 后端
- 使用Flake8进行代码检查
- 最大行长度：120字符
- 使用Black进行代码格式化
- 配置文件：backend/.flake8

#### 前端
- 使用ESLint进行代码检查
- 使用Prettier进行代码格式化

### 开发流程

1. 创建功能分支
2. 实现功能
3. 运行测试
4. 提交代码
5. 创建Pull Request

### 测试

- 后端：使用pytest进行单元测试
- 前端：使用Vitest进行组件和集成测试

## CI/CD

### GitHub Actions

配置好以下secrets：
- `DOCKER_USERNAME` - Docker Hub用户名
- `DOCKER_PASSWORD` - Docker Hub密码
- `SSH_KEY` - 服务器SSH私钥（用于部署）

### GitLab CI

在 Settings > CI/CD > Variables 中配置：
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `SSH_KEY`
- 其他必要的环境变量

## 技术亮点

### SQL提取算法
- 实现了复杂SQL语句的表名提取算法
- 支持多种SQL语法和嵌套查询
- 解决了传统方法在处理复杂SQL时的局限性

### 任务调度系统
- 使用APScheduler实现精准的定时任务调度
- 支持Cron表达式和间隔调度
- 任务状态监控和日志记录

### AI集成
- 集成阿里云通义千问API
- 提供智能SQL优化建议
- 自动分析SQL执行计划

### 性能优化
- 使用连接池管理数据库连接
- 任务异步执行，避免阻塞
- 优化的SQL查询和索引策略

## 项目状态

### 已完成功能
- ✅ 慢SQL管理和优化
- ✅ 数据库连接管理
- ✅ 执行计划分析
- ✅ 任务调度与执行
- ✅ 执行日志管理
- ✅ Docker支持
- ✅ CI/CD流水线
- ✅ 定时任务调度

### 计划功能
- 🔄 完善的测试套件
- 🔄 用户认证与权限管理
- 🔄 更详细的性能分析图表
- 🔄 多租户支持
- 🔄 更多数据库类型支持

## 版权信息

© 2024 数据库运维管理平台. All rights reserved.
