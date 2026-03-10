# MobileLocalization

移动端翻译协作平台（iOS + Android），用于多语言翻译文件上传、浏览、在线编辑与跨平台同步。

## 功能概览

- 登录鉴权（JWT + Cookie + Bearer Token）
- 上传语言文件（iOS `.strings` / Android `.xml`）
- 按平台和语言浏览、下载已上传文件
- 三语编辑表格（`en` / `ar` / `tr`）
- 输入框失焦自动保存
- 非英文翻译跨平台自动同步（英文值一致时同步 `ar`、`tr`）

## 技术栈

- 后端：FastAPI + Uvicorn
- 前端：Vue 3 + Vite + Vue Router
- 存储：本地文件系统（`backend/storage`）

## 目录结构

```text
MobileLocalization/
├─ backend/
│  ├─ main.py            # FastAPI 服务与核心逻辑
│  ├─ config.yaml        # 登录配置（JWT、账号）
│  ├─ requirements.txt   # Python 依赖
│  └─ storage/           # 翻译文件存储目录
└─ frontend/
   ├─ src/               # 前端源码
   ├─ package.json       # 前端依赖与脚本
   └─ vite.config.js     # 开发代理配置
```

## 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+
- Docker 24+（容器部署时）
- Docker Compose v2（容器部署时）

## 快速启动

### 1) 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8003
```

后端地址：`http://127.0.0.1:8003`

### 2) 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

前端地址：`http://127.0.0.1:5173`

## 容器部署（推荐线上）

### 1) 准备端口配置（可选）

```bash
cp .env.example .env
```

默认端口如下：

- 前端：`5173`
- 后端：`8003`

可在 `.env` 中修改：

```dotenv
FRONTEND_PORT=5173
BACKEND_PORT=8003
```

### 2) 启动容器

```bash
docker compose up -d --build
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8003/api/health`

### 3) 常用容器命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启
docker compose restart

# 停止并移除容器
docker compose down
```

## 一键部署脚本

项目提供了脚本：`scripts/deploy.sh`

用途：

1. 检查环境（git / docker / compose）
2. 输出当前代码版本（如果本机有 git）
3. 执行 `docker compose up -d --build --remove-orphans`
4. 输出容器状态并做基础健康检查

使用方式：

```bash
# 使用当前工作区代码直接部署
./scripts/deploy.sh
```

注意：

- 脚本不会执行 `git fetch/pull/checkout`，只部署你当前目录里的代码。
- 脚本默认读取 `.env`（如果存在）中的端口配置。

## 认证配置（backend/config.yaml）

```yaml
auth:
  jwt_secret: "change_this_to_a_long_random_secret"
  jwt_exp_minutes: 720
  users:
    - username: "admin"
      password: "123456"
      enabled: true
```

说明：

- `jwt_exp_minutes` 单位是“分钟”，不是秒。
- `users` 里 `enabled: true` 的账号才允许登录。
- 首次使用请务必修改默认 `jwt_secret` 和密码。

## 存储路径映射

| 平台 | 语言 | 目录 |
| --- | --- | --- |
| iOS | en | `backend/storage/ios/en.lproj` |
| iOS | ar | `backend/storage/ios/ar.lproj` |
| iOS | tr | `backend/storage/ios/tr.lproj` |
| Android | en | `backend/storage/android/values` |
| Android | ar | `backend/storage/android/values-ar` |
| Android | tr | `backend/storage/android/values-tr` |

## API 概览

- `POST /api/auth/login`：登录
- `GET /api/auth/me`：获取登录态
- `POST /api/auth/logout`：退出
- `GET /api/health`：健康检查
- `GET /api/files`：按平台/语言列文件
- `GET /api/download`：下载文件
- `POST /api/upload`：上传文件（同平台同语言会覆盖）
- `GET /api/file-content`：读取文件文本
- `POST /api/file-content`：保存文件文本
- `GET /api/editor-table`：获取三语编辑数据
- `POST /api/editor-table`：保存编辑数据并触发跨平台同步

## 前端与后端联调说明

- 开发环境默认使用 Vite 代理：`/api -> http://127.0.0.1:8003`
- 如需直连其他后端地址，可设置 `VITE_API_BASE`（例如 `http://127.0.0.1:8003`）
- 前后端建议使用相同主机名（如都用 `127.0.0.1`），避免 Cookie 会话问题

## 常见行为说明

- 上传接口会先清理该平台该语言下的现有同类型文件，再写入新文件。
- 编辑器自动保存只在“失焦且内容变化”时触发。
- 跨平台同步逻辑只同步 `ar`、`tr`，并且要求两端英文值一致。

## License

本项目采用 [GNU Affero General Public License v3.0（或更高版本）](./LICENSE)。
