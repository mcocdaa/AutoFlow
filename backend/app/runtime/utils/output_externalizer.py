# @file /backend/app/runtime/utils/output_externalizer.py
# @brief 大输出落盘并返回索引，避免响应与 run.json 体积失控
# @create 2026-02-22 00:00:00

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def externalize_if_large(
    value: Any,
    *,
    artifacts_dir: Path,
    file_stem: str,
    max_bytes: int = 64 * 1024,
) -> Any:
    try:
        dumped = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception:
        dumped = json.dumps(str(value), ensure_ascii=False, separators=(",", ":"))

    raw = dumped.encode("utf-8")
    if len(raw) <= max_bytes:
        return value

    out_dir = artifacts_dir / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{file_stem}.json"
    out_path.write_bytes(raw)

    sha256 = hashlib.sha256(raw).hexdigest()
    rel = str(out_path.relative_to(artifacts_dir))
    return {"__artifact__": {"path": rel, "sha256": sha256, "size": len(raw)}}
