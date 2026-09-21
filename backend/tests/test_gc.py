# @file /backend/tests/test_gc.py
# @brief RunStoreGC 单元测试:TTL 过期与 LRU 配额清理
# @create 2026-09-20

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.runtime.models import RunResult
from app.runtime.storage import RunStore, RunStoreGC


def _create_dummy_run(
    artifacts_dir: Path,
    run_id: str,
    started_at: datetime,
    file_size_kb: int = 1,
) -> None:
    run_dir = artifacts_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run = RunResult(
        run_id=run_id,
        flow_name="dummy",
        status="success",
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=1),
        duration_ms=1000,
    )
    (run_dir / "run.json").write_text(
        json.dumps(run.model_dump(mode="json")), encoding="utf-8"
    )
    (run_dir / "data.bin").write_bytes(b"x" * (file_size_kb * 1024))


def test_run_store_gc_ttl_cleanup(tmp_path: Path):
    artifacts_dir = tmp_path / "artifacts"
    store = RunStore(artifacts_dir)
    gc = RunStoreGC(store, max_age_days=30, max_total_bytes=100 * 1024 * 1024)

    now = datetime.now(UTC)
    # 1. 35 days old (should be cleaned by TTL)
    _create_dummy_run(
        artifacts_dir, "run_old", now - timedelta(days=35), file_size_kb=10
    )
    # 2. 10 days old (should be retained)
    _create_dummy_run(
        artifacts_dir, "run_recent", now - timedelta(days=10), file_size_kb=10
    )

    stats = gc.run_gc()
    assert stats["runs_scanned"] == 2
    assert stats["runs_deleted_ttl"] == 1
    assert stats["runs_deleted_quota"] == 0
    assert stats["remaining_runs"] == 1

    assert not (artifacts_dir / "run_old").exists()
    assert (artifacts_dir / "run_recent").exists()


def test_run_store_gc_quota_lru_cleanup(tmp_path: Path):
    artifacts_dir = tmp_path / "artifacts"
    store = RunStore(artifacts_dir)
    # Total quota = 25 KB
    gc = RunStoreGC(store, max_age_days=30, max_total_bytes=25 * 1024)

    now = datetime.now(UTC)
    # Three runs, 10KB each. Total = 30KB > 25KB quota
    _create_dummy_run(artifacts_dir, "run_1", now - timedelta(days=5), file_size_kb=10)
    _create_dummy_run(artifacts_dir, "run_2", now - timedelta(days=3), file_size_kb=10)
    _create_dummy_run(artifacts_dir, "run_3", now - timedelta(days=1), file_size_kb=10)

    stats = gc.run_gc()
    assert stats["runs_scanned"] == 3
    assert stats["runs_deleted_ttl"] == 0
    assert stats["runs_deleted_quota"] == 1  # oldest (run_1) should be purged
    assert stats["remaining_runs"] == 2

    assert not (artifacts_dir / "run_1").exists()
    assert (artifacts_dir / "run_2").exists()
    assert (artifacts_dir / "run_3").exists()
