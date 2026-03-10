# MobileLocalization 部署文档

## 1. 适用范围

本文档用于部署 `MobileLocalization` 前后端服务，默认采用 Docker Compose。

- 前端：Vue 构建产物由 Nginx 提供服务
- 后端：FastAPI（Uvicorn）
- 数据：宿主机目录 `backend/storage` 持久化

## 2. 部署架构

- 前端容器：`mobile-localization-frontend`
  - 对外端口：`${FRONTEND_PORT}`（默认 `5173`）
  - 容器内端口：`80`
- 后端容器：`mobile-localization-backend`
  - 对外端口：`${BACKEND_PORT}`（默认 `8003`）
  - 容器内端口：`8003`
- 前端通过 Nginx 反向代理 `/api` 到后端容器 `backend:8003`

## 3. 环境要求

部署机需要安装：

- Git
- Docker（建议 24+）
- Docker Compose（`docker compose`）

检查命令：

```bash
git --version
docker --version
docker compose version
```

## 4. 首次部署

### 4.1 获取代码

```bash
git clone <你的仓库地址> MobileLocalization
cd MobileLocalization
```

### 4.2 配置端口（可选）

```bash
cp .env.example .env
```

`.env` 示例：

```dotenv
FRONTEND_PORT=5173
BACKEND_PORT=8003
```

### 4.3 配置登录信息（必须）

编辑 `backend/config.yaml`，至少修改以下内容：

- `auth.jwt_secret`
- `auth.users` 中的账号密码

示例：

```yaml
auth:
  jwt_secret: "replace_with_a_long_random_secret"
  jwt_exp_minutes: 720
  users:
    - username: "admin"
      password: "strong_password_here"
      enabled: true
```

### 4.4 启动服务

```bash
docker compose up -d --build
```

### 4.5 验证服务

```bash
docker compose ps
curl -f http://127.0.0.1:${BACKEND_PORT:-8003}/api/health
curl -I http://127.0.0.1:${FRONTEND_PORT:-5173}
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8003/api/health`

## 5. 一键部署（推荐）

项目提供脚本：`scripts/deploy.sh`

功能：

1. 检查 `git/docker/compose`
2. 输出当前代码版本（如果本机有 git）
3. 执行 `docker compose up -d --build --remove-orphans`
4. 输出容器状态与基础健康检查

使用方式：

```bash
# 使用当前工作区代码直接部署
./scripts/deploy.sh
```

说明：

- 脚本不会执行 `git fetch/pull/checkout`，仅部署当前目录中的代码。
- 脚本会自动读取 `.env` 中的端口。

## 6. 日常运维命令

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# 重启服务
docker compose restart

# 仅重建后端
docker compose up -d --build backend

# 停止并移除容器
docker compose down
```

## 7. 数据持久化与备份

### 7.1 持久化目录

- 翻译文件：`backend/storage`
- 登录配置：`backend/config.yaml`（以只读方式挂载到容器）

### 7.2 备份建议

部署前建议备份：

```bash
tar -czf backup_$(date +%F_%H%M%S).tar.gz backend/storage backend/config.yaml
```

## 8. 发布更新流程

### 方式 A：脚本更新

```bash
./scripts/deploy.sh
```

### 方式 B：手动更新

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose up -d --build
```

## 9. 回滚流程

按 Git 提交回滚：

```bash
git checkout <稳定版本提交号或tag>
docker compose up -d --build
```

如果需要回滚翻译数据，使用备份包恢复 `backend/storage` 后重启容器。

## 10. 常见问题排查

### 10.1 `failed to connect to docker API`

原因：Docker daemon 未启动。  
处理：启动 Docker Desktop 或系统 Docker 服务后重试。

### 10.2 前端可打开但接口 401

优先检查：

- `backend/config.yaml` 账号是否正确、`enabled: true`
- 浏览器是否禁用 Cookie
- 前后端是否通过同一主机访问（建议都用 `127.0.0.1`）

### 10.3 上传失败或文件未落盘

检查：

- `backend/storage` 权限是否可写
- `docker compose logs -f backend` 中是否有异常栈

### 10.4 容器反复重启

检查：

- `backend/config.yaml` 是否存在且格式合法
- 端口是否被占用（`5173`/`8003`）

## 11. 安全建议（生产）

- 强制修改默认账号和密码
- 使用足够长度的 `jwt_secret`
- 仅在内网暴露后端端口，外网通过网关/Nginx 统一入口
- 建议启用 HTTPS（反向代理层处理）
