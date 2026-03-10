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
  log "未检测到 git，将跳过版本信息输出。"
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

if command -v git >/dev/null 2>&1; then
  CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  CURRENT_SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
  if [[ -n "$CURRENT_BRANCH" && -n "$CURRENT_SHA" ]]; then
    log "当前代码版本: ${CURRENT_BRANCH} (${CURRENT_SHA})"
  fi
fi

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
