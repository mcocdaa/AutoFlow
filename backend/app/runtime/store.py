# @file /backend/app/runtime/store.py
# @brief 运行记录的最小存储（内存 + 产物落盘）
# @create 2026-02-21 00:00:00

from __future__ import annotations

import json
from pathlib import Path

from app.runtime.models import RunResult


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
        (run_dir / "run.json").write_text(
            json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

