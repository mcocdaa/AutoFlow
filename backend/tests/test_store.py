# @file /backend/tests/test_store.py
# @brief 测试 RunStore 落盘读取:跨实例可见、排序、删除、坏文件跳过
# @create 2026-09-15

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.runtime.models import RunResult, StepResult
from app.runtime.storage.store import RunStore


def _make_run(run_id: str, *, seconds: int = 0) -> RunResult:
    started = datetime(2026, 9, 15, 10, 0, seconds, tzinfo=UTC)
    return RunResult(
        run_id=run_id,
        flow_name="demo",
        status="success",
        started_at=started,
        finished_at=started,
        duration_ms=0,
        steps=[
            StepResult(
                step_id="s1",
                status="success",
                started_at=started,
                finished_at=started,
                duration_ms=0,
                action_output={"ok": True},
            )
        ],
        error=None,
    )


def test_run_visible_to_other_store_instance(tmp_path: Path) -> None:
    RunStore(artifacts_dir=tmp_path).save_run(_make_run("run-a"))

    run = RunStore(artifacts_dir=tmp_path).get_run("run-a")

    assert run.run_id == "run-a"
    assert run.steps[0].action_output == {"ok": True}
    assert run.started_at == datetime(2026, 9, 15, 10, 0, tzinfo=UTC)


def test_list_runs_sorted_by_started_at_desc(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    store.save_run(_make_run("run-a", seconds=0))
    store.save_run(_make_run("run-b", seconds=5))

    runs = store.list_runs()

    assert [run.run_id for run in runs] == ["run-b", "run-a"]


def test_delete_run_removes_artifacts(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    store.save_run(_make_run("run-a"))

    store.delete_run("run-a")

    assert not (tmp_path / "run-a").exists()
    with pytest.raises(KeyError):
        store.get_run("run-a")


def test_list_runs_skips_corrupt_file(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    store.save_run(_make_run("run-a"))
    bad_dir = tmp_path / "run-bad"
    bad_dir.mkdir()
    (bad_dir / "run.json").write_text("{not-json", encoding="utf-8")

    runs = store.list_runs()

    assert [run.run_id for run in runs] == ["run-a"]


def test_request_round_trip_across_instances(tmp_path: Path) -> None:
    payload = {
        "flow_yaml": 'version: "1"',
        "input": {"items": [1, 2]},
        "vars": {"dry_run": True},
    }
    RunStore(artifacts_dir=tmp_path).save_request("run-a", payload)

    assert RunStore(artifacts_dir=tmp_path).get_request("run-a") == payload


def test_get_request_missing_raises_key_error(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)

    with pytest.raises(KeyError):
        store.get_request("run-a")


def test_delete_run_removes_request(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    store.save_run(_make_run("run-a"))
    store.save_request("run-a", {"flow_yaml": 'version: "1"', "vars": {}})

    store.delete_run("run-a")

    assert not (tmp_path / "run-a").exists()
