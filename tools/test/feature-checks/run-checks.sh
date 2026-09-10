#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../../.." && pwd)

# 优先使用后端 venv,否则退回系统 python3
if [ -x "${REPO_ROOT}/backend/.venv/bin/python" ]; then
    PYTHON="${REPO_ROOT}/backend/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "${SCRIPT_DIR}/run-checks.py" "$@"
