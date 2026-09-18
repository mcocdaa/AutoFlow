# @file /backend/tests/test_api_fork.py
# @brief 测试 POST /debug/sessions/fork:成功分叉、继续执行与异常分支
# @create 2026-09-18

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.api.v1 import debug as debug_module
from app.core.registry import Registry
from app.main import app
from app.runtime.loaders import load_flow_spec_from_yaml_text
from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner import Runner
from app.runtime.storage.store import RunStore
from fastapi.testclient import TestClient

FLOW_YAML = """\
version: "1"
name: fork-api-demo
steps:
  - id: s1
    action:
      type: test.echo
      params:
        message: one
    output_var: first
  - id: s2
    action:
      type: test.echo
      params:
        message: "{{vars.first.message}}-two"
  - id: s3
    action:
      type: test.echo
      params:
        message: "{{steps.s2.output.message}}-three"
"""


def _echo_action(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {"message": params.get("message", "ok")}


def _setup(monkeypatch, tmp_path: Path) -> tuple[TestClient, Registry, RunStore, str]:
    registry = Registry()
    registry.register_action("test.echo", _echo_action)
    store = RunStore(artifacts_dir=tmp_path / "artifacts")
    monkeypatch.setattr(debug_module, "get_registry", lambda: registry)
    monkeypatch.setattr(debug_module, "get_store", lambda: store)

    flow = FlowSpec(
        version="1",
        name="fork-api-demo",
        steps=[
            StepSpec(
                id="s1",
                action=ActionSpec(type="test.echo", params={"message": "one"}),
                output_var="first",
            ),
            StepSpec(
                id="s2",
                action=ActionSpec(
                    type="test.echo", params={"message": "{{vars.first.message}}-two"}
                ),
            ),
            StepSpec(
                id="s3",
                action=ActionSpec(
                    type="test.echo",
                    params={"message": "{{steps.s2.output.message}}-three"},
                ),
            ),
        ],
    )
    request = {"flow_yaml": FLOW_YAML, "input": None, "vars": {}}
    source = Runner(registry, store).run_flow(flow, request=request)

    return TestClient(app), registry, store, source.run_id


def test_fork_then_step_and_run(monkeypatch, tmp_path: Path) -> None:
    client, _, store, run_id = _setup(monkeypatch, tmp_path)

    response = client.post(
        "/api/v1/debug/sessions/fork",
        json={"run_id": run_id, "next_step_index": 2},
    )

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["parent_run_id"] == run_id
    assert snapshot["fork_step_index"] == 2
    assert snapshot["index"] == 2
    assert [r["step_id"] for r in snapshot["results"]] == ["s1", "s2"]

    session_id = snapshot["session_id"]
    stepped = client.post(f"/api/v1/debug/sessions/{session_id}/step")
    assert stepped.status_code == 200
    assert stepped.json()["status"] == "success"

    forked = store.get_run(session_id)
    assert forked.parent_run_id == run_id
    assert forked.steps[-1].action_output["message"] == "one-two-three"


def test_fork_retry_failed_step(monkeypatch, tmp_path: Path) -> None:
    client, _, store, _ = _setup(monkeypatch, tmp_path)
    registry = debug_module.get_registry()
    flow_yaml = (
        'version: "1"\nname: fork-api-fail\nsteps:\n'
        "  - id: ok\n    action:\n      type: test.echo\n"
        "  - id: bad\n    action:\n      type: test.fail\n"
    )
    flow = load_flow_spec_from_yaml_text(flow_yaml)
    attempts = {"count": 0}

    def flaky(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    registry.register_action("test.fail", flaky)
    request = {"flow_yaml": flow_yaml, "input": None, "vars": {}}
    failed = Runner(registry, store).run_flow(flow, request=request)
    assert failed.status == "failed"

    response = client.post(
        "/api/v1/debug/sessions/fork",
        json={"run_id": failed.run_id, "next_step_index": 1},
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    finished = client.post(f"/api/v1/debug/sessions/{session_id}/run")
    assert finished.status_code == 200
    assert finished.json()["status"] == "success"


def test_fork_error_branches(monkeypatch, tmp_path: Path) -> None:
    client, registry, store, run_id = _setup(monkeypatch, tmp_path)

    missing = client.post(
        "/api/v1/debug/sessions/fork",
        json={"run_id": "missing", "next_step_index": 0},
    )
    assert missing.status_code == 404

    out_of_range = client.post(
        "/api/v1/debug/sessions/fork",
        json={"run_id": run_id, "next_step_index": 99},
    )
    assert out_of_range.status_code == 400

    no_request = Runner(registry, store).run_flow(
        FlowSpec(
            version="1",
            name="no-request",
            steps=[StepSpec(id="s1", action=ActionSpec(type="test.echo"))],
        )
    )
    no_req_response = client.post(
        "/api/v1/debug/sessions/fork",
        json={"run_id": no_request.run_id, "next_step_index": 0},
    )
    assert no_req_response.status_code == 404
    assert no_req_response.json()["detail"] == "run has no stored request"
