#!/bin/bash
# ============================================
# AutoFlow 停止脚本
# 用法:
#   ./stop.sh <mode>
#   mode: dev | prod
# 示例:
#   ./stop.sh dev    # 开发模式停止
#   ./stop.sh prod   # 生产模式停止
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

usage() {
    echo "用法: $0 <mode>"
    echo "  mode: dev | prod"
    echo ""
    echo "示例:"
    echo "  $0 dev   # 开发模式停止"
    echo "  $0 prod  # 生产模式停止"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

MODE="$1"

cd "$DOCKER_DIR"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

echo "========================================"
echo "AutoFlow 停止"
echo "========================================"
echo "模式: $MODE"
echo "========================================"

docker compose -p autoflow \
    -f docker-compose.base.yml \
    -f docker-compose.backend.yml \
    -f docker-compose.frontend.yml down

echo ""
echo "✓ 停止完成"
echo "========================================"
