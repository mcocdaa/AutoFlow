#!/bin/bash
set -e

# 工具版本（统一管控，避免版本不一致）
DETECT_SECRETS_VERSION="1.4.0"

# 安装逻辑（容器内优先用pip安装，无sudo）
function install_detect_secrets() {
    echo "[INFO] 开始安装 detect-secrets==${DETECT_SECRETS_VERSION}"
    # 安装指定版本的detect-secrets
    pip install detect-secrets==${DETECT_SECRETS_VERSION}
    # 验证安装
    if detect-secrets --version &> /dev/null; then
        echo "[SUCCESS] detect-secrets 安装完成，版本：$(detect-secrets --version)"
    else
        echo "[ERROR] detect-secrets 安装失败"
        exit 1
    fi
}

# 主流程
install_detect_secrets
