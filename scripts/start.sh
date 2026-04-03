#!/bin/bash

# ============================================
# 极简项目启动脚本 - AutoFlow
# ============================================

PROJECT="autoflow"
ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$ROOT")"
FRONT_DIR="$PROJECT_ROOT/frontend"
BACK_DIR="$PROJECT_ROOT/backend"
DOCKER_DIR="$PROJECT_ROOT/docker"

BACK_PORT=3000      # 本地后端端口
FRONT_PORT=5180     # 本地前端端口

# 帮助信息
if [ $# -ne 2 ]; then
    cat << EOF
用法: $0 <模式> <服务>

模式:
  local  - 本地直接运行 (Python/Node)
  dev    - Docker Compose 开发模式
  prod   - Docker Swarm 生产模式

服务:
  frontend  - 仅前端
  backend   - 仅后端
  full      - 前后端全部

示例:
  $0 local full      # 本地启动前后端
  $0 dev backend     # Docker 仅后端
  $0 prod full       # 生产部署
EOF
    exit 1
fi

MODE=$1
SERVICE=$2

# 加载 .env
[ -f "$PROJECT_ROOT/.env" ] && export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)

# 清理残留进程（避免端口冲突）
cleanup() {
    echo "→ 清理现有服务..."
    docker compose -p "$PROJECT" down 2>/dev/null || true
    docker stack rm "$PROJECT" 2>/dev/null || true
    lsof -ti:$BACK_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONT_PORT | xargs kill -9 2>/dev/null || true
}

# 本地后端启动（自动检测 Poetry 或 pip）
start_backend_local() {
    echo "→ 启动后端..."
    cd "$BACK_DIR"

    [ ! -d ".venv" ] && python3 -m venv .venv
    source .venv/bin/activate

    if command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
        poetry install && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port $BACK_PORT &
    else
        pip install -r requirements.txt
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BACK_PORT &
    fi
    echo "✓ 后端: http://localhost:$BACK_PORT"
}

# 本地前端启动
start_frontend_local() {
    echo "→ 启动前端..."
    cd "$FRONT_DIR"

    [ ! -d "node_modules" ] && npm install

    PORT=$FRONT_PORT npm run dev &
    echo "✓ 前端: http://localhost:$FRONT_PORT"
}

# Docker 启动（自动组合 compose 文件）
start_docker() {
    cleanup

    local files="-f $DOCKER_DIR/docker-compose.base.yml"
    [ "$SERVICE" != "frontend" ] && files="$files -f $DOCKER_DIR/docker-compose.backend.yml"
    [ "$SERVICE" != "backend" ] && files="$files -f $DOCKER_DIR/docker-compose.frontend.yml"

    if [ "$MODE" = "prod" ]; then
        echo "→ 生产模式部署..."
        docker stack deploy $files "$PROJECT"
    else
        echo "→ 开发模式启动..."
        docker compose -p "$PROJECT" $files up --build -d
    fi

    echo ""
    echo "✓ 启动完成"
}

# 主路由
case $MODE in
    local)
        cleanup
        case $SERVICE in
            backend)  start_backend_local; wait ;;
            frontend) start_frontend_local; wait ;;
            full)     start_backend_local; echo "→ 等 3s 启动前端..."; sleep 3; start_frontend_local; wait ;;
            *)        echo "错误: 服务必须是 frontend/backend/full"; exit 1 ;;
        esac
        ;;
    dev|prod)
        start_docker
        ;;
    *)
        echo "错误: 模式必须是 local/dev/prod"; exit 1 ;;
esac
