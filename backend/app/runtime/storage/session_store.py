# @file /backend/app/runtime/storage/session_store.py
# @brief 调试会话落盘存储(_sessions/<id>.json + 跨进程文件锁)
# @create 2026-09-15

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - 非 POSIX 平台降级为无锁
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SessionStore:
    """调试会话状态落盘,多 worker 共享同一份会话

    - 每个会话一个 JSON 文件:`_sessions/<session_id>.json`,临时文件 + 原子替换;
    - `locked()` 用 fcntl.flock 提供跨进程互斥,读改写期间持有锁;
    - 会话目录无 run.json,RunStore.list_runs 会自然跳过。
    """

    def __init__(self, artifacts_dir: Path) -> None:
        self._dir = artifacts_dir / "_sessions"
        self._dir.mkdir(parents=True, exist_ok=True)

    def exists(self, session_id: str) -> bool:
        return self._path(session_id).is_file()

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False, indent=2, default=str)
        tmp_path = self._dir / f"{session_id}.json.tmp"
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self._path(session_id))

    def get(self, session_id: str) -> dict[str, Any]:
        path = self._path(session_id)
        if not path.is_file():
            raise KeyError(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def delete(self, session_id: str) -> None:
        self._path(session_id).unlink(missing_ok=True)

    @contextmanager
    def locked(self, session_id: str) -> Iterator[None]:
        """跨进程独占锁:包裹会话的读-改-写全过程"""
        handle = open(self._lock_path(session_id), "w", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.json"

    def _lock_path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.lock"
