#!/bin/bash
set -euo pipefail
# ============================================
# AutoFlow 初始化 Docker Secrets
# 从 .env 读取密码并写入 secrets/ 目录下的文件
# Docker Compose 使用这些文件作为 secrets 挂载到容器
#
# 用法: ./scripts/init-secrets.sh
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_DIR="$PROJECT_ROOT/secrets"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "错误: .env 文件不存在"
    echo "请先复制模板: cp .env.example .env"
    exit 1
fi

# 用 set -a 方式加载，支持含空格/特殊字符的值
set -a
# shellcheck source=/dev/null
source "$PROJECT_ROOT/.env"
set +a

# 检查必需变量
: "${DB_PASSWORD:?请在 .env 中设置 DB_PASSWORD}"
: "${MYSQL_ROOT_PASSWORD:?请在 .env 中设置 MYSQL_ROOT_PASSWORD}"
: "${SECRET_KEY:?请在 .env 中设置 SECRET_KEY}"

mkdir -p "$SECRETS_DIR"

printf '%s' "$DB_PASSWORD"          > "$SECRETS_DIR/db_password"
printf '%s' "$MYSQL_ROOT_PASSWORD"  > "$SECRETS_DIR/mysql_root_password"
printf '%s' "$SECRET_KEY"           > "$SECRETS_DIR/secret_key"

chmod 600 "$SECRETS_DIR/db_password" \
          "$SECRETS_DIR/mysql_root_password" \
          "$SECRETS_DIR/secret_key"

echo "✓ Secrets 初始化完成:"
echo "  $SECRETS_DIR/db_password"
echo "  $SECRETS_DIR/mysql_root_password"
echo "  $SECRETS_DIR/secret_key"
