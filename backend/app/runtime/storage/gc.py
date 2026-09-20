# @file /backend/app/runtime/storage/gc.py
# @brief 运行记录与产物垃圾回收 (RunStoreGC) - 默认 30 天 TTL + 5GB 配额自动 LRU 清理
# @create 2026-09-20

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.runtime.storage.store import RunStore

logger = logging.getLogger(__name__)

DEFAULT_MAX_AGE_DAYS = 30
DEFAULT_MAX_TOTAL_BYTES = 5 * 1024 * 1024 * 1024  # 5GB
DEFAULT_GC_INTERVAL_SECONDS = 3600.0  # 1 hour


@dataclass
class RunInfo:
    run_id: str
    path: Path
    started_at: datetime
    size_bytes: int


def _dir_size(path: Path) -> int:
    """递归统计目录下所有文件大小 (字节)"""
    total = 0
    if not path.exists():
        return 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


class RunStoreGC:
    """运行产物与记录的垃圾回收器

    机制:
    1. TTL 过期清理: 删除启动时间超过 max_age_days (默认 30 天) 的历史运行
    2. LRU 配额控制: 若总占用超过 max_total_bytes (默认 5GB)，按启动时间/最后访问从旧到新逐个淘汰
    3. 孤立产物清理: 清理 outputs/ 中超期文件
    """

    def __init__(
        self,
        store: RunStore,
        *,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
        interval_seconds: float = DEFAULT_GC_INTERVAL_SECONDS,
    ) -> None:
        self.store = store
        self.max_age_days = max_age_days
        self.max_total_bytes = max_total_bytes
        self.interval_seconds = interval_seconds

    @property
    def artifacts_dir(self) -> Path:
        return self.store.artifacts_dir

    def _inspect_runs(self) -> list[RunInfo]:
        """扫描 artifacts_dir 提取每个 run 的启动时间与体积"""
        runs: list[RunInfo] = []
        if not self.artifacts_dir.is_dir():
            return runs

        for entry in self.artifacts_dir.iterdir():
            if not entry.is_dir() or entry.name in ("outputs", "temp", "tmp"):
                continue

            run_id = entry.name
            run_json = entry / "run.json"
            started_at: datetime | None = None

            if run_json.is_file():
                try:
                    data = json.loads(run_json.read_text(encoding="utf-8"))
                    raw_time = data.get("started_at")
                    if raw_time:
                        started_at = datetime.fromisoformat(raw_time)
                        if started_at.tzinfo is None:
                            started_at = started_at.replace(tzinfo=UTC)
                except Exception:
                    pass

            if started_at is None:
                try:
                    mtime = entry.stat().st_mtime
                    started_at = datetime.fromtimestamp(mtime, tz=UTC)
                except OSError:
                    started_at = datetime.now(UTC)

            size = _dir_size(entry)
            runs.append(
                RunInfo(
                    run_id=run_id,
                    path=entry,
                    started_at=started_at,
                    size_bytes=size,
                )
            )

        return runs

    def run_gc(self) -> dict[str, Any]:
        """执行一次完整的 GC 周期并返回统计信息"""
        now = datetime.now(UTC)
        ttl_cutoff = now - timedelta(days=self.max_age_days)

        runs = self._inspect_runs()
        runs_scanned = len(runs)
        runs_deleted_ttl = 0
        runs_deleted_quota = 0
        freed_bytes = 0

        # 阶段 1: TTL 清理
        surviving_runs: list[RunInfo] = []
        for run_info in runs:
            if run_info.started_at < ttl_cutoff:
                logger.info("GC deleting expired run (TTL): %s", run_info.run_id)
                self.store.delete_run(run_info.run_id)
                runs_deleted_ttl += 1
                freed_bytes += run_info.size_bytes
            else:
                surviving_runs.append(run_info)

        # 阶段 2: LRU 配额控制 (从旧到新淘汰)
        surviving_runs.sort(key=lambda r: r.started_at)
        total_bytes = sum(r.size_bytes for r in surviving_runs)

        while total_bytes > self.max_total_bytes and surviving_runs:
            oldest = surviving_runs.pop(0)
            logger.info(
                "GC deleting run for quota (LRU, %d bytes): %s",
                oldest.size_bytes,
                oldest.run_id,
            )
            self.store.delete_run(oldest.run_id)
            runs_deleted_quota += 1
            freed_bytes += oldest.size_bytes
            total_bytes -= oldest.size_bytes

        # 阶段 3: 清理 outputs/ 下过期的孤立大文件
        outputs_dir = self.artifacts_dir / "outputs"
        if outputs_dir.is_dir():
            for f in outputs_dir.iterdir():
                if f.is_file():
                    try:
                        f_mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
                        if f_mtime < ttl_cutoff:
                            f_size = f.stat().st_size
                            f.unlink(missing_ok=True)
                            freed_bytes += f_size
                    except OSError:
                        pass

        remaining_runs = len(surviving_runs)
        remaining_bytes = sum(r.size_bytes for r in surviving_runs)

        stats = {
            "runs_scanned": runs_scanned,
            "runs_deleted_ttl": runs_deleted_ttl,
            "runs_deleted_quota": runs_deleted_quota,
            "total_freed_bytes": freed_bytes,
            "remaining_runs": remaining_runs,
            "remaining_bytes": remaining_bytes,
        }
        logger.info("RunStoreGC cycle finished: %s", stats)
        return stats

    async def start_gc_loop(self, stop_event: asyncio.Event | None = None) -> None:
        """后台异步循环协程"""
        logger.info(
            "RunStoreGC background coroutine started (interval=%.1fs, ttl=%ddays, quota=%.1fGB)",
            self.interval_seconds,
            self.max_age_days,
            self.max_total_bytes / (1024 * 1024 * 1024),
        )
        while True:
            try:
                self.run_gc()
            except Exception as e:
                logger.exception("Error during RunStoreGC execution: %s", e)

            if stop_event is not None:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.interval_seconds
                    )
                    logger.info("RunStoreGC received stop signal, exiting loop.")
                    break
                except TimeoutError:
                    pass
            else:
                await asyncio.sleep(self.interval_seconds)
