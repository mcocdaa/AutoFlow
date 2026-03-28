#!/bin/bash
# ============================================
# Secrets 分级验证脚本
# required: 缺失时报错阻断
# optional: 缺失时警告继续
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_DIR="${ROOT_DIR}/secrets"

# 颜色定义
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# 定义 secrets 列表: 文件名:描述:级别
# 级别: required | optional
SECRETS_LIST=(
    "db_password:数据库密码:required"
    "secret_key:应用密钥:required"
    "mysql_root_password:MySQL root 密码:required"
)

check_secret() {
    local file="$1"
    local desc="$2"
    local level="$3"
    local filepath="${SECRETS_DIR}/${file}"

    if [[ ! -f "$filepath" ]]; then
        echo "missing:${level}:${file}:${desc}"
        return 1
    fi

    if [[ ! -s "$filepath" ]]; then
        echo "empty:${level}:${file}:${desc}"
        return 1
    fi

    return 0
}

main() {
    local missing_required=()
    local empty_required=()
    local missing_optional=()
    local empty_optional=()

    echo "🔐 检查 Secrets..."
    echo ""

    # 检查目录
    if [[ ! -d "$SECRETS_DIR" ]]; then
        echo -e "${RED}❌ secrets 目录不存在${NC}"
        echo ""
        echo "💡 修复方法:"
        echo "   mkdir -p secrets"
        echo "   bash scripts/init-secrets.sh"
        exit 1
    fi

    # 检查每个 secret
    for item in "${SECRETS_LIST[@]}"; do
        IFS=':' read -r file desc level <<< "$item"
        result=$(check_secret "$file" "$desc" "$level" 2>&1 || true)

        if [[ -n "$result" ]]; then
            IFS=':' read -r status lvl f d <<< "$result"
            if [[ "$lvl" == "required" ]]; then
                if [[ "$status" == "missing" ]]; then
                    missing_required+=("$f ($d)")
                else
                    empty_required+=("$f ($d)")
                fi
            else
                if [[ "$status" == "missing" ]]; then
                    missing_optional+=("$f ($d)")
                else
                    empty_optional+=("$f ($d)")
                fi
            fi
        fi
    done

    # 处理 required 缺失（报错阻断）
    if [[ ${#missing_required[@]} -gt 0 || ${#empty_required[@]} -gt 0 ]]; then
        echo -e "${RED}❌ 必需的 Secrets 配置不完整${NC}"
        echo ""

        if [[ ${#missing_required[@]} -gt 0 ]]; then
            echo "📂 缺失的文件:"
            for item in "${missing_required[@]}"; do
                echo "   - $item"
            done
        fi

        if [[ ${#empty_required[@]} -gt 0 ]]; then
            echo "📄 为空的文件:"
            for item in "${empty_required[@]}"; do
                echo "   - $item"
            done
        fi

        echo ""
        echo -e "${RED}🚫 启动已阻断，请修复后重试${NC}"
        echo ""
        echo "💡 修复方法:"
        echo "   bash scripts/init-secrets.sh    # 自动生成随机密钥"
        echo "   # 或手动创建并编辑 secrets/ 下的文件"
        exit 1
    fi

    # 处理 optional 缺失（警告继续）
    if [[ ${#missing_optional[@]} -gt 0 || ${#empty_optional[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  可选的 Secrets 未配置${NC}"
        echo ""

        if [[ ${#missing_optional[@]} -gt 0 ]]; then
            echo "📂 缺失的文件（可选）:"
            for item in "${missing_optional[@]}"; do
                echo "   - $item"
            done
        fi

        if [[ ${#empty_optional[@]} -gt 0 ]]; then
            echo "📄 为空的文件（可选）:"
            for item in "${empty_optional[@]}"; do
                echo "   - $item"
            done
        fi

        echo ""
        echo "✅ 继续启动（可选功能将不可用）"
        echo ""
    else
        echo -e "${GREEN}✅ 所有 Secrets 配置正确${NC}"
    fi
}

main "$@"
