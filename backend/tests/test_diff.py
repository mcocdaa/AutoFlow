# @file /backend/tests/test_diff.py
# @brief 测试 deep_diff 工具、步骤对齐与运行 diff API
# @create 2026-09-18

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.api.v1 import runs as runs_module
from app.core.registry import Registry
from app.main import app
from app.runtime.models import ActionSpec, FlowSpec, RunResult, StepResult, StepSpec
from app.runtime.runner import Runner
from app.runtime.storage.store import RunStore
from app.runtime.utils.diff import align_steps, deep_diff, step_diff
from fastapi.testclient import TestClient

STARTED = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)


def _step(step_id: str, *, output: Any = None, status: str = "success") -> StepResult:
    return StepResult(
        step_id=step_id,
        status=status,  # type: ignore[arg-type]
        started_at=STARTED,
        finished_at=STARTED,
        duration_ms=0,
        action_output=output,
    )


def _run(name: str, *steps: StepResult) -> RunResult:
    return RunResult(
        run_id=f"{name}-id",
        flow_name=name,
        status="success",
        started_at=STARTED,
        finished_at=STARTED,
        duration_ms=1,
        steps=list(steps),
    )


def test_deep_diff_scalar_and_nested() -> None:
    base = {"a": 1, "b": {"c": "x", "d": [1, 2]}}
    target = {"a": 2, "b": {"c": "x", "d": [1, 3]}, "e": True}

    diff = deep_diff(base, target)

    paths = {entry["path"] for entry in diff}
    assert "$.a" in paths
    assert "$.b.d[1]" in paths
    assert "$.e" in paths
    assert "$.b.c" not in paths


def test_deep_diff_list_length() -> None:
    diff = deep_diff([1, 2, 3], [1])

    assert {"path": "$.length", "base": 3, "target": 1} in diff


def test_deep_diff_respects_limit() -> None:
    base = {str(i): 0 for i in range(50)}
    target = {str(i): 1 for i in range(50)}

    diff = deep_diff(base, target, limit=10)

    assert len(diff) == 10


def test_align_steps_matches_and_appends_target_only() -> None:
    base = [_step("a"), _step("b"), _step("removed")]
    target = [_step("a"), _step("b"), _step("added")]

    aligned = align_steps(base, target)

    assert [
        (b.step_id if b else None, t.step_id if t else None) for _, b, _, t in aligned
    ] == [
        ("a", "a"),
        ("b", "b"),
        ("removed", None),
        (None, "added"),
    ]


def test_step_diff_reports_changes() -> None:
    base = _step("a", output={"x": 1})
    target = _step("a", output={"x": 2})

    diff = step_diff(0, base, 0, target)

    assert diff["output_changed"] is True
    assert diff["output_diff"] == [{"path": "$.x", "base": 1, "target": 2}]
    assert diff["status_changed"] is False


def test_step_diff_check_change() -> None:
    base = _step("a", output={})
    base.check_passed = True
    target = _step("a", output={})
    target.check_passed = False

    diff = step_diff(0, base, 0, target)

    assert diff["check_changed"] is True


def _echo_action(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {"message": params.get("message", "ok")}


def _flow() -> FlowSpec:
    return FlowSpec(
        version="1",
        name="diff-demo",
        steps=[
            StepSpec(
                id="s1",
                action=ActionSpec(
                    type="test.echo", params={"message": "{{input.name}}"}
                ),
            ),
            StepSpec(
                id="s2",
                action=ActionSpec(
                    type="test.echo",
                    params={"message": "{{steps.s1.output.message}}-x"},
                ),
            ),
        ],
    )


def test_diff_api(monkeypatch, tmp_path: Path) -> None:
    registry = Registry()
    registry.register_action("test.echo", _echo_action)
    store = RunStore(artifacts_dir=tmp_path / "artifacts")
    monkeypatch.setattr(runs_module, "get_store", lambda: store)
    runner = Runner(registry, store)

    base = runner.run_flow(_flow(), input={"name": "A"})
    target = runner.run_flow(_flow(), input={"name": "B"})

    client = TestClient(app)
    response = client.get(f"/api/v1/runs/{base.run_id}/diff/{target.run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["base"]["run_id"] == base.run_id
    assert payload["target"]["run_id"] == target.run_id
    assert len(payload["steps"]) == 2
    assert payload["steps"][0]["output_changed"] is True
    assert payload["steps"][0]["output_diff"][0]["path"] == "$.message"

    missing = client.get(f"/api/v1/runs/{base.run_id}/diff/missing")
    assert missing.status_code == 404
