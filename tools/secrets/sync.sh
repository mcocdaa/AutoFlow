#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
secrets_dir="${SECRETS_DIR:-$root_dir/secrets}"

if [[ ! -d "$secrets_dir" ]]; then
    echo "secrets 目录不存在: $secrets_dir" >&2
    exit 1
fi

shopt -s nullglob
key_files=("$secrets_dir"/*.key)
if (( ${#key_files[@]} == 0 )); then
    exit 0
fi

for src in "${key_files[@]}"; do
    dest="${src%.key}"
    tmp="${dest}.tmp.$$"

    printf '%s' "$(cat "$src")" > "$tmp"
    chmod 600 "$tmp" 2>/dev/null || true

    if [[ ! -f "$dest" ]] || ! cmp -s "$tmp" "$dest"; then
        mv -f "$tmp" "$dest"
    else
        rm -f "$tmp"
    fi
done

if [[ "${1:-}" == "--clean-key" ]]; then
    rm -f "${key_files[@]}"
fi
