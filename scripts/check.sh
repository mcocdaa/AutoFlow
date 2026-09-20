#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/backend"
echo "==> [AutoFlow] Backend ruff check..."
uv run ruff check --config pyproject.toml app ../plugins
echo "==> [AutoFlow] Backend pytest..."
uv run pytest -q

cd "$PROJECT_ROOT/frontend"
echo "==> [AutoFlow] Frontend lint..."
npm run lint

echo "✓ 全部检查通过 (AutoFlow)"
