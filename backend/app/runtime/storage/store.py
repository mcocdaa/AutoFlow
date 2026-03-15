# @file /backend/app/runtime/storage/store.py
# @brief 运行记录的最小存储（内存 + 产物落盘）
# @create 2026-02-21 00:00:00
# @update 2026-03-15 修复循环引用导致的序列化问题

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.runtime.models import RunResult


def _deep_copy_with_ref_tracking(obj: Any, seen: dict[int, Any] | None = None) -> Any:
    if seen is None:
        seen = {}

    obj_id = id(obj)
    if obj_id in seen:
        return seen[obj_id]

    if isinstance(obj, dict):
        result = {}
        seen[obj_id] = result
        for k, v in obj.items():
            result[k] = _deep_copy_with_ref_tracking(v, seen)
        return result

    if isinstance(obj, list):
        result = []
        seen[obj_id] = result
        for item in obj:
            result.append(_deep_copy_with_ref_tracking(item, seen))
        return result

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    try:
        return copy.deepcopy(obj)
    except Exception:
        return str(obj)


class RunStore:
    def __init__(self, artifacts_dir: Path) -> None:
        self._runs: dict[str, RunResult] = {}
        self._artifacts_dir = artifacts_dir

    @property
    def artifacts_dir(self) -> Path:
        return self._artifacts_dir

    def save_run(self, run: RunResult) -> None:
        self._runs[run.run_id] = run
        self._write_run_artifact(run)

    def get_run(self, run_id: str) -> RunResult:
        return self._runs[run_id]

    def list_runs(self) -> list[RunResult]:
        return list(self._runs.values())

    def _write_run_artifact(self, run: RunResult) -> None:
        run_dir = self._artifacts_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        data = _deep_copy_with_ref_tracking(run.model_dump(mode="python"))
        (run_dir / "run.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
