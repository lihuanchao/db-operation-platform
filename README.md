已创建的配置文件
1. Docker 支持
Dockerfile.backend - 后端服务的 Docker 镜像构建配置
Dockerfile.frontend - 前端服务的 Docker 镜像构建配置
docker-compose.yml - 本地开发和测试的 Docker 编排配置
nginx.conf - Nginx 反向代理和静态资源服务器配置
.dockerignore - 构建过程中忽略的文件和目录列表
2. CI/CD 流水线
github/workflows/ci.yml - GitHub Actions 持续集成和部署配置
.gitlab-ci.yml - GitLab CI 持续集成和部署配置
功能概述
Docker 镜像特点
轻量级基础镜像：使用 Alpine Linux 和 Python 3.12-slim
依赖管理：使用虚拟环境和缓存优化
健康检查：集成健康检查机制
时区设置：默认使用 Asia/Shanghai 时区
数据卷：持久化存储和代码映射
编排服务
后端服务（Flask）- 5000 端口
前端服务（Vue 3 + Nginx）- 80 端口
MySQL 数据库 - 3306 端口
phpMyAdmin（可选）- 8080 端口
CI/CD 流程
分支保护：只有 main/master 分支才会自动构建和部署
缓存优化：利用 GitHub/GitLab 缓存机制
依赖检查：包括代码 linting、测试、构建
部署选项：支持自动部署到服务器
使用说明
本地开发

# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
生产部署

# 使用生产环境变量
cp .env.example .env
# 编辑 .env 文件配置生产环境
docker-compose up -d
CI/CD 配置
GitHub Actions：配置好 secrets（DOCKER_USERNAME、DOCKER_PASSWORD、SSH_KEY 等）
GitLab CI：在 Settings > CI/CD > Variables 中配置变量
现在您已经具备了完整的 Docker 支持和 CI/CD 流水线，可以方便地进行开发、测试和部署！