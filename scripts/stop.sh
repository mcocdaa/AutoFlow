#!/bin/bash
set -euo pipefail
# ============================================
# AutoFlow 停止脚本
# 用法: ./scripts/stop.sh <mode> [service]
#   mode:    dev | prod
#   service: backend | frontend | full（默认 full）
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

usage() {
    echo "用法: $0 <mode> [service]"
    echo "  mode:    dev | prod"
    echo "  service: backend | frontend | full（默认 full）"
    echo ""
    echo "示例:"
    echo "  $0 dev           # 停止全部（dev 模式）"
    echo "  $0 dev backend   # 停止仅后端"
    echo "  $0 prod          # 停止生产 stack"
    exit 1
}

[ $# -lt 1 ] && usage

MODE="$1"
SERVICE="${2:-full}"

# 加载 .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

echo "========================================"
echo "AutoFlow 停止 [mode=$MODE, service=$SERVICE]"
echo "========================================"

if [ "$MODE" = "prod" ]; then
    docker stack rm autoflow
    echo "等待服务移除..."
    sleep 5
else
    # 根据 service 组合 compose 文件（与 start.sh 保持一致）
    files="-f $DOCKER_DIR/docker-compose.base.yml"
    [ "$SERVICE" != "frontend" ] && files="$files -f $DOCKER_DIR/docker-compose.backend.yml"
    [ "$SERVICE" != "backend"  ] && files="$files -f $DOCKER_DIR/docker-compose.frontend.yml"

    docker compose \
        --env-file "$PROJECT_ROOT/.env" \
        -p autoflow \
        $files \
        down 2>/dev/null || true
fi

echo ""
echo "✓ 停止完成"
echo "========================================"
