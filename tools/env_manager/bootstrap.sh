#!/bin/bash
set -e

echo "[BOOTSTRAP] Checking env_manager requirements..."

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[BOOTSTRAP] Python3 not found. Installing..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y python3 python3-pip
    elif command -v apk &> /dev/null; then
        apk add --no-cache python3 py3-pip
    else
        echo "[ERROR] Unsupported package manager. Please install Python3 manually."
        exit 1
    fi
fi

# 2. Check PyYAML
if ! python3 -c "import yaml" &> /dev/null; then
    echo "[BOOTSTRAP] PyYAML not found. Installing..."
    # Try system package first for speed/stability in containers
    if command -v apt-get &> /dev/null; then
        apt-get install -y python3-yaml || pip3 install pyyaml
    elif command -v apk &> /dev/null; then
        apk add --no-cache py3-yaml || pip3 install pyyaml
    else
        pip3 install pyyaml
    fi
fi

# 3. Check Poetry (needed for backend)
if ! command -v poetry &> /dev/null; then
    echo "[BOOTSTRAP] Poetry not found. Installing..."
    pip3 install poetry
fi

echo "[BOOTSTRAP] env_manager is ready."
