# @file /backend/app/runtime/storage/store.py
# @brief 运行记录存储(run.json 落盘,多进程/重启后可见)
# @create 2026-02-21 00:00:00
# @update 2026-03-15 修复循环引用导致的序列化问题
# @update 2026-08-10 序列化收敛至 app.runtime.utils.serialization.safe_deep_copy
# @update 2026-09-15 由进程内存改为落盘读取,支持多 worker 与重启后历史

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from app.runtime.models import RunResult
from app.runtime.utils.serialization import safe_deep_copy
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class RunStore:
    """每个 run 持久化为 artifacts_dir/<run_id>/run.json

    读路径直接读盘:多 worker 之间看到同一份运行记录,进程重启后历史不丢失。
    写入使用临时文件 + 原子替换,避免并发读取到半截 JSON。
    """

    def __init__(self, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    @property
    def artifacts_dir(self) -> Path:
        return self._artifacts_dir

    def save_run(self, run: RunResult) -> None:
        run_dir = self._artifacts_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        data = safe_deep_copy(run.model_dump(mode="python"))
        payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        tmp_path = run_dir / "run.json.tmp"
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(run_dir / "run.json")

    def save_request(self, run_id: str, payload: dict[str, Any]) -> None:
        """持久化执行请求(flow_yaml/input/vars),用于回放"""
        run_dir = self._artifacts_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = run_dir / "request.json.tmp"
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        tmp_path.replace(run_dir / "request.json")

    def get_request(self, run_id: str) -> dict[str, Any]:
        path = self._artifacts_dir / run_id / "request.json"
        if not path.is_file():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def get_run(self, run_id: str) -> RunResult:
        path = self._artifacts_dir / run_id / "run.json"
        if not path.is_file():
            raise KeyError(run_id)
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def list_runs(self) -> list[RunResult]:
        runs: list[RunResult] = []
        for run_dir in sorted(self._artifacts_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            path = run_dir / "run.json"
            if not path.is_file():
                continue
            try:
                run = RunResult.model_validate_json(path.read_text(encoding="utf-8"))
                runs.append(run)
            except (ValidationError, ValueError, OSError) as e:
                logger.warning("Skip unreadable run %s: %s", run_dir.name, e)
        runs.sort(key=lambda run: run.started_at, reverse=True)
        return runs

    def delete_run(self, run_id: str) -> None:
        run_dir = self._artifacts_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
