#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mode="${1:-dev}"

if [[ "$mode" == "-h" || "$mode" == "--help" ]]; then
    echo "Usage: $0 [dev|prod]"
    exit 0
fi

if [[ "$mode" == "prod" ]]; then
    bash "$root_dir/tools/secrets/sync.sh" --clean-key
else
    bash "$root_dir/tools/secrets/sync.sh"
fi
