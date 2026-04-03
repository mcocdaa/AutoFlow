#!/bin/bash
set -euo pipefail
# ============================================
# AutoFlow 启动脚本
# ============================================

PROJECT="autoflow"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONT_DIR="$PROJECT_ROOT/frontend"
BACK_DIR="$PROJECT_ROOT/backend"
DOCKER_DIR="$PROJECT_ROOT/docker"

# 帮助信息
usage() {
    cat << EOF
用法: $0 <模式> <服务>

模式:
  local  - 本地直接运行 (Python + npm dev server)
  dev    - Docker Compose 开发模式
  prod   - Docker Swarm 生产模式

服务:
  backend   - 仅后端（含 MySQL / Redis）
  frontend  - 前后端全部，仅暴露前端端口
  full      - 前后端全部

示例:
  $0 local full      # 本地启动前后端
  $0 dev backend     # Docker 仅后端
  $0 dev full        # Docker 全栈
  $0 prod full       # 生产部署
EOF
    exit 1
}

[ $# -ne 2 ] && usage

MODE=$1
SERVICE=$2

# 加载 .env（支持含空格/特殊字符的值）
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

# 默认值（未设 .env 时生效）
BACKEND_EXTERNAL_PORT="${BACKEND_EXTERNAL_PORT:-3001}"
FRONTEND_DEV_PORT="${FRONTEND_DEV_PORT:-5181}"
FRONTEND_EXTERNAL_PORT="${FRONTEND_EXTERNAL_PORT:-8001}"

# ---- 清理函数 ----

cleanup_ports() {
    echo "→ 清理端口占用..."
    lsof -ti:"$BACKEND_EXTERNAL_PORT"  | xargs kill -9 2>/dev/null || true
    lsof -ti:"$FRONTEND_DEV_PORT"      | xargs kill -9 2>/dev/null || true
}

cleanup_docker() {
    echo "→ 停止已有容器..."
    docker compose -p "$PROJECT" down 2>/dev/null || true
    docker stack rm "$PROJECT" 2>/dev/null || true
}

# ---- 本地启动函数 ----

start_backend_local() {
    echo "→ 启动后端..."
    cd "$BACK_DIR"

    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    # shellcheck source=/dev/null
    source .venv/bin/activate

    if command -v poetry &>/dev/null && [ -f "pyproject.toml" ]; then
        poetry install --quiet
        poetry run uvicorn app.main:app \
            --reload --host "${HOST:-0.0.0.0}" --port "$BACKEND_EXTERNAL_PORT" &
    else
        pip install -r requirements.txt -q
        python -m uvicorn app.main:app \
            --reload --host "${HOST:-0.0.0.0}" --port "$BACKEND_EXTERNAL_PORT" &
    fi
    echo "✓ 后端: http://localhost:$BACKEND_EXTERNAL_PORT"
}

start_frontend_local() {
    echo "→ 启动前端..."
    cd "$FRONT_DIR"

    if [ ! -d "node_modules" ]; then
        npm install
    fi

    npm run dev -- --port "$FRONTEND_DEV_PORT" &
    echo "✓ 前端: http://localhost:$FRONTEND_DEV_PORT"
}

# ---- Docker 启动函数 ----

start_docker() {
    cleanup_docker

    # 确保 secrets 文件存在
    if [ ! -f "$PROJECT_ROOT/secrets/db_password" ]; then
        echo "→ 初始化 secrets..."
        "$SCRIPT_DIR/init-secrets.sh"
    fi

    # 组合 compose 文件
    local files="-f $DOCKER_DIR/docker-compose.base.yml"
    [ "$SERVICE" != "frontend" ] && files="$files -f $DOCKER_DIR/docker-compose.backend.yml"
    [ "$SERVICE" != "backend"  ] && files="$files -f $DOCKER_DIR/docker-compose.frontend.yml"

    if [ "$MODE" = "prod" ]; then
        echo "→ 生产模式部署 (Docker Swarm)..."
        docker stack deploy $files "$PROJECT"
    else
        echo "→ 开发模式启动 (Docker Compose)..."
        docker compose \
            --env-file "$PROJECT_ROOT/.env" \
            -p "$PROJECT" \
            $files \
            up --build -d
    fi

    echo ""
    echo "✓ 启动完成"
    [ "$SERVICE" != "frontend" ] && echo "  后端: http://localhost:$BACKEND_EXTERNAL_PORT"
    [ "$SERVICE" != "backend"  ] && echo "  前端: http://localhost:$FRONTEND_EXTERNAL_PORT"
}

# ---- 主路由 ----

case $MODE in
    local)
        cleanup_ports
        case $SERVICE in
            backend)
                start_backend_local
                wait
                ;;
            frontend)
                start_frontend_local
                wait
                ;;
            full)
                start_backend_local
                echo "→ 等待后端就绪 (3s)..."
                sleep 3
                start_frontend_local
                wait
                ;;
            *)
                echo "错误: 服务必须是 backend / frontend / full"
                exit 1
                ;;
        esac
        ;;
    dev|prod)
        start_docker
        ;;
    *)
        echo "错误: 模式必须是 local / dev / prod"
        exit 1
        ;;
esac
