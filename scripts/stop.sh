#!/bin/bash
# ============================================
# AutoFlow 停止脚本（Docker 全栈）
# 用法: ./stop.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
docker compose -p autoflow down

echo "✓ 已停止"
