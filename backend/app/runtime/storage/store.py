# @file /backend/app/runtime/storage/store.py
# @brief 运行记录的最小存储（内存 + 产物落盘）
# @create 2026-02-21 00:00:00
# @update 2026-03-15 修复循环引用导致的序列化问题
# @update 2026-08-10 序列化收敛至 app.runtime.utils.serialization.safe_deep_copy

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.runtime.models import RunResult
from app.runtime.utils.serialization import safe_deep_copy


class RunStore:
    """In-memory run store backed by optional JSON artifacts on disk.

    Important: Runs are stored in a process-local dict and are NOT shared
    across workers. Runs are also lost on restart. This is acceptable for
    single-process development and light usage; for production multi-worker
    deployments, replace with a shared store (e.g. database, Redis, etc.).
    """

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

    def delete_run(self, run_id: str) -> None:
        """Delete a run from the in-memory store and its artifacts directory."""
        self._runs.pop(run_id, None)
        run_dir = self._artifacts_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)

    def _write_run_artifact(self, run: RunResult) -> None:
        run_dir = self._artifacts_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        data = safe_deep_copy(run.model_dump(mode="python"))
        (run_dir / "run.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
