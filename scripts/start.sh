#!/bin/bash
# ============================================
# 通用项目启动脚本
# 支持 Docker (开发/生产) 和 本地 模式启动前后端
# ============================================

# ================== 【配置区域】 在此处修改项目特定配置 ==================

# --- 1. 项目基本信息 ---
PROJECT_NAME="autoflow"           # 项目英文名 (用于 Docker 命名空间)
PROJECT_DISPLAY_NAME="AutoFlow"   # 项目显示名 (用于日志输出)

# --- 2. 目录结构 (相对于项目根目录) ---
# 注意：脚本默认位于项目根目录下的某子目录中（如 ./scripts/）
DOCKER_SUBDIR="docker"             # Docker 配置文件目录
FRONTEND_SUBDIR="frontend"         # 前端代码目录
BACKEND_SUBDIR="backend"           # 后端代码目录
SCRIPT_SUBDIR="scripts"            # 辅助脚本目录 (如 check-secrets.sh)

# --- 3. 端口配置 ---
BACKEND_LOCAL_PORT=3000            # 本地后端服务端口
BACKEND_DOCKER_PORT=3001           # Docker 后端映射端口
FRONTEND_LOCAL_PORT=5180           # 本地前端服务端口 (Vite/Webpack)
FRONTEND_DOCKER_PORT=8001          # Docker 前端映射端口

# --- 4. Docker Compose 配置文件名 (位于 DOCKER_SUBDIR 下) ---
COMPOSE_BASE="docker-compose.base.yml"
COMPOSE_BACKEND="docker-compose.backend.yml"
COMPOSE_FRONTEND="docker-compose.frontend.yml"

# --- 5. 后端启动配置 (Python) ---
BACKEND_UVICORN_ENTRY="app.main:app"  # Uvicorn 入口点
BACKEND_POETRY_INSTALL=true            # 是否使用 Poetry 安装依赖
BACKEND_REQUIREMENTS_FILE=""           # 如果不使用 Poetry，指定 requirements.txt (可选)

# --- 6. 前端启动配置 (Node.js) ---
FRONTEND_PKG_MGR="npm"                 # 包管理器 (npm/yarn/pnpm)
FRONTEND_DEV_CMD="npm run dev"         # 本地开发启动命令
FRONTEND_DEV_ENV_VARS=("DOCKER_WEB=true") # 本地启动所需环境变量

# --- 7. 其他工具配置 ---
ENV_EXAMPLE_FILE=".env.example"
ENV_FILE=".env"
SECRETS_CHECK_SCRIPT="check-secrets.sh"

# ================== 【配置区域结束】 以下代码通常无需修改 ==================

set -e

# --- 路径计算 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")" # 假设脚本在根目录下的一级子目录 (如 scripts/)
DOCKER_DIR="$PROJECT_ROOT/$DOCKER_SUBDIR"
FRONTEND_DIR="$PROJECT_ROOT/$FRONTEND_SUBDIR"
BACKEND_DIR="$PROJECT_ROOT/$BACKEND_SUBDIR"

# --- 帮助信息 ---
usage() {
    echo "用法: $0 <mode> [service]"
    echo ""
    echo "  Mode (模式):"
    echo "    dev    - 开发模式 (使用 Docker Compose)"
    echo "    local  - 本地模式 (直接在宿主机运行 Node/Python)"
    echo "    prod   - 生产模式 (使用 Docker Swarm)"
    echo ""
    echo "  Service (服务):"
    echo "    backend       - 仅启动后端"
    echo "    frontend      - 仅启动前端 (Docker模式下有效)"
    echo "    frontend-local - 仅启动前端 (强制本地模式，通常配合 dev mode 使用)"
    echo "    full          - 启动前后端 (默认)"
    echo ""
    echo "示例:"
    echo "  $0 dev backend         # Docker 开发模式 - 仅后端"
    echo "  $0 dev frontend-local  # Docker 开发模式后端 + 本地前端调试"
    echo "  $0 local full          # 纯本地开发 (前后端都在本机运行)"
    echo "  $0 prod full           # 生产环境部署"
    exit 1
}

if [ $# -lt 1 ]; then usage; fi

MODE="$1"
SERVICE="${2:-full}"

# --- 核心功能函数 ---

stop_services() {
    echo "停止现有服务..."
    if [ "$MODE" = "prod" ]; then
        docker stack rm "$PROJECT_NAME" 2>/dev/null || true
        echo "等待 Swarm 服务移除..."
        sleep 5
    else
        docker compose -p "$PROJECT_NAME" -f "$DOCKER_DIR/$COMPOSE_BASE" down 2>/dev/null || true
    fi
    echo "服务停止完成"
}

init_env_file() {
    if [ ! -f "$PROJECT_ROOT/$ENV_FILE" ]; then
        echo "创建环境配置文件: $ENV_FILE"
        cp "$PROJECT_ROOT/$ENV_EXAMPLE_FILE" "$PROJECT_ROOT/$ENV_FILE"
    fi
}

load_env() {
    if [ -f "$PROJECT_ROOT/$ENV_FILE" ]; then
        echo "加载环境变量..."
        export $(grep -v '^#' "$PROJECT_ROOT/$ENV_FILE" | xargs)
    fi
}

check_secrets() {
    local secret_script="$SCRIPT_DIR/$SECRETS_CHECK_SCRIPT"
    if [ -f "$secret_script" ]; then
        echo "检查密钥配置..."
        bash "$secret_script"
    fi
}

# --- 本地启动逻辑 ---

start_backend_local() {
    echo ">>> 启动本地后端..."
    cd "$BACKEND_DIR"

    # 1. 虚拟环境检查
    if [ ! -d ".venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate

    # 2. 依赖安装
    if [ "$BACKEND_POETRY_INSTALL" = true ]; then
        if ! command -v poetry &> /dev/null; then
            echo "安装 Poetry..."
            pip install poetry
        fi
        poetry install
    elif [ -n "$BACKEND_REQUIREMENTS_FILE" ]; then
        pip install -r "$BACKEND_REQUIREMENTS_FILE"
    fi

    # 3. 启动服务
    echo "后端服务将在 http://localhost:$BACKEND_LOCAL_PORT 启动"
    poetry run uvicorn "$BACKEND_UVICORN_ENTRY" --reload --host 0.0.0.0 --port "$BACKEND_LOCAL_PORT" &
    BACKEND_PID=$!
    echo "本地后端 PID: $BACKEND_PID"
}

start_frontend_local() {
    echo ">>> 启动本地前端..."
    cd "$FRONTEND_DIR"

    # 1. 依赖检查
    if [ ! -d "node_modules" ]; then
        echo "安装前端依赖 ($FRONTEND_PKG_MGR)..."
        $FRONTEND_PKG_MGR install
    fi

    # 2. 启动服务
    echo "前端服务将在 http://localhost:$FRONTEND_LOCAL_PORT 启动"
    echo "按 Ctrl+C 停止前端服务"

    # 导入环境变量并执行
    export "${FRONTEND_DEV_ENV_VARS[@]}"
    cd "$FRONTEND_DIR" && $FRONTEND_DEV_CMD
}

# --- 主逻辑路由 ---

# 1. 处理纯本地模式 (Local Mode)
if [ "$MODE" = "local" ]; then
    load_env
    case "$SERVICE" in
        backend)
            start_backend_local
            ;;
        frontend|frontend-local)
            start_frontend_local
            ;;
        full)
            start_backend_local
            echo "等待后端启动..."
            sleep 3
            start_frontend_local
            ;;
        *)
            echo "错误: 未知服务 '$SERVICE'"
            usage
            ;;
    esac
    exit 0
fi

# 2. 处理 Docker 模式 (Dev/Prod)
# 构建 Compose 文件参数
COMPOSE_ARGS="-f $DOCKER_DIR/$COMPOSE_BASE"
case "$SERVICE" in
    backend)
        COMPOSE_ARGS="$COMPOSE_ARGS -f $DOCKER_DIR/$COMPOSE_BACKEND"
        ;;
    frontend)
        COMPOSE_ARGS="$COMPOSE_ARGS -f $DOCKER_DIR/$COMPOSE_FRONTEND"
        ;;
    frontend-local)
        # 特殊逻辑：Docker模式下只启动Backend，Frontend留给用户本地启
        COMPOSE_ARGS="$COMPOSE_ARGS -f $DOCKER_DIR/$COMPOSE_BACKEND"
        echo "注意: frontend-local 模式将仅在 Docker 中启动后端，前端请手动在本地启动。"
        ;;
    full)
        COMPOSE_ARGS="$COMPOSE_ARGS -f $DOCKER_DIR/$COMPOSE_BACKEND -f $DOCKER_DIR/$COMPOSE_FRONTEND"
        ;;
    *)
        echo "错误: 未知服务 '$SERVICE'"
        usage
        ;;
esac

# 执行 Docker 启动前准备
cd "$DOCKER_DIR"
init_env_file
load_env
check_secrets
stop_services

# 显示启动信息
echo ""
echo "========================================"
echo "  $PROJECT_DISPLAY_NAME 启动中..."
echo "========================================"
echo "模式:    $MODE"
echo "服务:    $SERVICE"
echo "========================================"

# 执行启动
if [ "$MODE" = "prod" ]; then
    docker stack deploy -c "$DOCKER_DIR/$COMPOSE_BASE" -c "$DOCKER_DIR/$COMPOSE_BACKEND" "$PROJECT_NAME"
else
    docker compose -p "$PROJECT_NAME" $COMPOSE_ARGS up --build -d
fi

# 输出访问信息
echo ""
echo "启动完成!"
echo "========================================"
if [ "$SERVICE" = "backend" ] || [ "$SERVICE" = "full" ] || [ "$SERVICE" = "frontend-local" ]; then
    echo "后端 API: http://localhost:${BACKEND_DOCKER_PORT}"
    echo "API 文档: http://localhost:${BACKEND_DOCKER_PORT}/docs"
fi
if [ "$SERVICE" = "frontend" ] || [ "$SERVICE" = "full" ]; then
    echo "前端界面: http://localhost:${FRONTEND_DOCKER_PORT}"
fi
if [ "$SERVICE" = "frontend-local" ]; then
    echo ""
    echo "提示: 请在 '$FRONTEND_SUBDIR' 目录下手动启动前端以连接 Docker 后端。"
fi
echo ""
