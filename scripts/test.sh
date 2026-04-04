#!/bin/bash
set -euo pipefail
# ============================================
# AutoFlow 测试脚本
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONT_DIR="$PROJECT_ROOT/frontend"
BACK_DIR="$PROJECT_ROOT/backend"

# 帮助信息
usage() {
    cat << EOF
用法: $0 <服务>

服务:
  backend   - 仅测试后端（pytest）
  frontend  - 仅测试前端（vue-tsc）
  full      - 前后端全部测试

示例:
  $0 backend     # 测试后端
  $0 frontend    # 测试前端
  $0 full        # 测试全部
EOF
    exit 1
}

[ $# -ne 1 ] && usage

SERVICE=$1

# 测试后端
test_backend() {
    echo "→ 测试后端..."
    cd "$BACK_DIR"

    if [ ! -f "pyproject.toml" ]; then
        echo "错误: 未找到 pyproject.toml"
        exit 1
    fi

    if command -v poetry &>/dev/null; then
        poetry run pytest -v
    elif [ -d ".venv" ]; then
        .venv/bin/python -m pytest -v
    else
        echo "错误: 未找到 poetry 或 .venv，请先安装依赖"
        exit 1
    fi
}

# 测试前端
test_frontend() {
    echo "→ 测试前端..."
    cd "$FRONT_DIR"

    if [ ! -d "node_modules" ]; then
        echo "错误: 未找到 node_modules，请先运行 start.sh local frontend 安装依赖"
        exit 1
    fi

    npm run build
}

# 主路由
case $SERVICE in
    backend)
        test_backend
        ;;
    frontend)
        test_frontend
        ;;
    full)
        test_backend
        echo ""
        test_frontend
        echo ""
        echo "✓ 全部测试完成"
        ;;
    *)
        echo "错误: 服务必须是 backend / frontend / full"
        usage
        ;;
esac
