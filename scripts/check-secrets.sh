#!/bin/bash
# ============================================
# Secrets 检查脚本
# 后端已无 secrets 消费者(DB/Redis 死配置已移除),
# 本脚本保留以维持 start.sh 调用链,仅输出提示。
# ============================================

set -euo pipefail

echo "🔐 检查 Secrets..."
echo ""
echo "  后端不再消费 DB/Redis secrets,无需检查"
echo ""
echo "✅ Secrets 检查通过"
