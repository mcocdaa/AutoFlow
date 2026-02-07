#!/bin/bash
set -e  # 出错立即退出，避免静默失败

# ===================== 配置区（可按需修改） =====================
# 当前脚本所在目录（自动获取，无需手动改）
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# 配置文件路径（指定当前文件夹下的.cfg）
CONFIG_FILE="${SCRIPT_DIR}/.detect-secrets.cfg"
# 基线文件路径
BASELINE_FILE="${SCRIPT_DIR}/.secrets.baseline"
# 要扫描的根目录（AutoFlow 项目根目录，可根据实际调整）
SCAN_ROOT=$(cd "${SCRIPT_DIR}/../../../../../" && pwd)
# ===================== 核心逻辑 =====================

# 1. 检查detect-secrets是否安装
function check_dependency() {
    if ! command -v detect-secrets &> /dev/null; then
        echo "[INFO] detect-secrets未安装，正在自动安装..."
        pip install detect-secrets>=1.4.0
        if [ $? -ne 0 ]; then
            echo "[ERROR] detect-secrets安装失败，请手动执行：pip install detect-secrets"
            exit 1
        fi
    fi
}

# 2. 检查配置文件是否存在
function check_config() {
    if [ ! -f "${CONFIG_FILE}" ]; then
        echo "[ERROR] 配置文件不存在：${CONFIG_FILE}"
        exit 1
    fi
}

# 3. 执行扫描（手动指定配置文件）
function run_scan() {
    echo "[INFO] 开始扫描 AutoFlow 项目，扫描根目录：${SCAN_ROOT}"
    echo "[INFO] 使用配置文件：${CONFIG_FILE}"

    # 核心命令：--config 指定自定义配置文件路径
    detect-secrets scan \
        --config "${CONFIG_FILE}" \
        --update "${BASELINE_FILE}" \
        "${SCAN_ROOT}"

    echo "[SUCCESS] 扫描完成！"
    echo "[INFO] 基线文件路径：${BASELINE_FILE}"
    echo "[INFO] 如需查看扫描结果，执行：detect-secrets audit ${BASELINE_FILE}"
}

# 主流程
check_dependency
check_config
run_scan
