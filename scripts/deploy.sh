#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

if ! command -v git >/dev/null 2>&1; then
  fail "git 未安装，无法拉取代码。"
fi
if ! command -v docker >/dev/null 2>&1; then
  fail "docker 未安装，无法部署容器。"
fi

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  fail "未检测到 docker compose（docker compose 或 docker-compose）。"
fi

GIT_REMOTE="${GIT_REMOTE:-origin}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
if [[ -z "$BRANCH" || "$BRANCH" == "HEAD" ]]; then
  fail "无法识别当前分支，请显式传入分支名：scripts/deploy.sh <branch>"
fi

log "准备拉取代码并部署: remote=${GIT_REMOTE}, branch=${BRANCH}"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH" --track "${GIT_REMOTE}/${BRANCH}"
fi

git pull "$GIT_REMOTE" "$BRANCH"

CURRENT_SHA="$(git rev-parse --short HEAD)"
log "当前代码版本: ${BRANCH} (${CURRENT_SHA})"

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-1}"
log "已启用 BuildKit 构建加速"

log "开始构建并启动容器"
"${DC[@]}" up -d --build --remove-orphans

log "当前容器状态"
"${DC[@]}" ps

if command -v curl >/dev/null 2>&1; then
  FRONTEND_PORT="${FRONTEND_PORT:-5173}"
  BACKEND_PORT="${BACKEND_PORT:-8003}"
  sleep 2
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null; then
    log "后端健康检查通过: http://127.0.0.1:${BACKEND_PORT}/api/health"
  else
    log "后端健康检查未通过，请查看日志"
  fi
  if curl -fsS "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null; then
    log "前端可访问: http://127.0.0.1:${FRONTEND_PORT}"
  else
    log "前端访问检查未通过，请查看日志"
  fi
fi

log "部署完成"
