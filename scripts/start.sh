#!/bin/bash
# ============================================
# AutoFlow 启动脚本（唯一入口）
#
# 用法:
#   ./start.sh                    # Docker 全栈（默认）: 构建并启动单镜像
#   ./start.sh local [service]    # 本地开发进程: all | backend | frontend（默认 all）
#
# 示例:
#   ./start.sh
#   ./start.sh local
#   ./start.sh local backend
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

usage() {
    echo "用法: $0 [docker|local] [service]"
    echo "  docker        构建并启动全栈容器（默认）"
    echo "  local [svc]   本地开发进程, svc: all | backend | frontend（默认 all）"
    exit 1
}

init_env() {
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        echo "[init] 未找到 .env,已从 .env.example 创建"
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    fi
}

load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/.env"
        set +a
    fi
}

start_backend_local() {
    echo "[backend] 检查依赖..."
    cd "$BACKEND_DIR"
    uv sync
    echo "[backend] 启动 http://localhost:${BACKEND_EXTERNAL_PORT:-3001}"
    uv run uvicorn app.main:app --reload \
        --host "${HOST:-0.0.0.0}" --port "${BACKEND_EXTERNAL_PORT:-3001}" &
}

start_frontend_local() {
    echo "[frontend] 检查依赖..."
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        (cd "$FRONTEND_DIR" && npm install)
    fi
    echo "[frontend] 启动 http://localhost:5180"
    (cd "$FRONTEND_DIR" && DOCKER_WEB=true npm run dev) &
}

run_docker() {
    docker compose -p autoflow up -d --build
    echo ""
    echo "✓ 已启动: http://localhost:${BACKEND_EXTERNAL_PORT:-3001}"
    echo "  前端 / API / Swagger 同端口 (docs: /docs)"
}

MODE="${1:-docker}"

case "$MODE" in
    docker)
        init_env
        load_env
        run_docker
        ;;
    local)
        SERVICE="${2:-all}"
        init_env
        load_env
        case "$SERVICE" in
            all)
                start_backend_local
                sleep 3
                start_frontend_local
                echo ""
                echo "✓ 本地开发已启动 (后端 3001 / 前端 5180), Ctrl+C 退出"
                wait
                ;;
            backend)
                start_backend_local
                wait
                ;;
            frontend)
                start_frontend_local
                wait
                ;;
            *)
                usage
                ;;
        esac
        ;;
    *)
        usage
        ;;
esac
