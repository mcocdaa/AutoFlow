#!/bin/bash
# ============================================
# Secrets 初始化脚本
# 后端已无 secrets 消费者(DB/Redis 死配置已移除),
# 本脚本保留以维持调用链,不再生成任何 secret 文件。
# ============================================

set -euo pipefail

echo "🔐 初始化 Secrets"
echo "=================="
echo ""
echo "  后端不再消费 DB/Redis secrets,无需初始化"
echo ""
echo "✅ Secrets 初始化完成(无需操作)"
