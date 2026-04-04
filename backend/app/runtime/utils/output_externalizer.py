# @file /backend/app/runtime/utils/output_externalizer.py
# @brief 大输出落盘与索引返回 - 将超出阈值的输出写入文件并返回路径引用
# @create 2026-02-22 00:00:00

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def externalize_if_large(
    value: Any,
    artifacts_dir: Path,
    file_stem: str = "output",
    max_bytes: int = 64 * 1024,
) -> Any | dict[str, Any]:
    if not isinstance(value, (str, bytes, bytearray)):
        return value

    raw: bytes = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    if len(raw) <= max_bytes:
        return value

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    suffix = hashlib.md5(raw, usedforsecurity=False).hexdigest()[:12]
    rel_path = f"{file_stem}_{suffix}.txt"
    target = artifacts_dir / rel_path
    target.write_text(value if isinstance(value, str) else raw.decode("utf-8", errors="replace"))

    return {"__artifact__": {"path": rel_path}}
