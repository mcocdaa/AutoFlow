#!/bin/bash
# ============================================
# Secrets 初始化脚本
# 自动创建缺失的 secrets 文件并生成随机值
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_DIR="${ROOT_DIR}/secrets"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

generate_password() {
    openssl rand -base64 32 | tr -d '=+/' | cut -c1-24
}

generate_key() {
    openssl rand -hex 32
}

init_secret() {
    local filename="$1"
    local description="$2"
    local generator="$3"
    local filepath="${SECRETS_DIR}/${filename}"

    if [[ -f "$filepath" && -s "$filepath" ]]; then
        echo "  ✅ $description 已存在"
        return 0
    fi

    local value
    value=$($generator)
    echo "$value" > "$filepath"
    chmod 600 "$filepath"
    echo -e "  ${GREEN}✅ 已生成: $description${NC}"
}

main() {
    echo "🔐 初始化 Secrets"
    echo "=================="
    echo ""

    # 创建目录
    if [[ ! -d "$SECRETS_DIR" ]]; then
        mkdir -p "$SECRETS_DIR"
        echo "📁 创建目录: secrets/"
        echo ""
    fi

    # 初始化各文件
    init_secret "db_password" "数据库密码" generate_password
    init_secret "mysql_root_password" "MySQL root 密码" generate_password
    init_secret "secret_key" "应用密钥" generate_key

    echo ""
    echo -e "${GREEN}🎉 Secrets 初始化完成${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  注意:${NC}"
    echo "   - 自动生成的密钥仅适用于开发环境"
    echo "   - 生产环境请手动设置强密码"
    echo "   - 请勿提交 secrets/ 目录到版本控制"
}

main "$@"
