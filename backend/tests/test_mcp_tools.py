# @file /backend/tests/test_mcp_tools.py
# @brief 测试 MCP 工具实现:能力发现、同步/异步执行、回放、产物读取
# @create 2026-09-18

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from app.core.registry import Registry
from app.mcp.tools import (
    McpDeps,
    get_artifact,
    get_run,
    list_capabilities,
    list_flows,
    list_runs,
    replay_run_sync,
    run_flow_sync,
    start_run_async,
)
from app.runtime.runner import Runner
from app.runtime.storage.store import RunStore

INLINE_FLOW = """\
version: "1"
name: inline-demo
steps:
  - id: s1
    action:
      type: test.echo
      params:
        message: hello
"""


def _echo_action(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {"message": params.get("message", "ok")}


def _make_deps(tmp_path: Path) -> McpDeps:
    registry = Registry()
    registry.register_action("test.echo", _echo_action)
    store = RunStore(artifacts_dir=tmp_path / "artifacts")
    runner = Runner(registry, store)
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    return McpDeps(registry=registry, store=store, runner=runner, flows_dir=flows_dir)


def test_run_flow_sync_persists_request_and_replays(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)

    result = run_flow_sync(deps, flow_yaml=INLINE_FLOW, input={"n": 1}, vars={"x": 2})

    assert result["status"] == "success"
    assert result["steps"][0]["step_id"] == "s1"
    assert deps.store.get_request(result["run_id"])["input"] == {"n": 1}

    replayed = replay_run_sync(deps, result["run_id"])

    assert replayed["run_id"] != result["run_id"]
    assert replayed["status"] == "success"
    assert replayed["flow_name"] == "inline-demo"


def test_run_flow_sync_from_flows_dir(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)
    (deps.flows_dir / "want.flow.yaml").write_text(
        INLINE_FLOW.replace("inline-demo", "from-dir"), encoding="utf-8"
    )

    result = run_flow_sync(deps, flow_name="want")

    assert result["flow_name"] == "from-dir"
    assert result["status"] == "success"


def test_run_flow_requires_exactly_one_source(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)

    with pytest.raises(ValueError):
        run_flow_sync(deps)
    with pytest.raises(ValueError):
        run_flow_sync(deps, flow_name="x", flow_yaml=INLINE_FLOW)


def test_start_run_async_poll_until_finished(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)

    started = start_run_async(deps, flow_yaml=INLINE_FLOW)

    assert started["status"] == "running"
    deadline = time.time() + 10
    while time.time() < deadline:
        run = get_run(deps, started["run_id"])
        if run["status"] != "running":
            break
        time.sleep(0.05)

    assert run["status"] == "success"
    assert run["steps"][0]["status"] == "success"


def test_get_run_missing_raises(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)

    with pytest.raises(ValueError):
        get_run(deps, "missing")


def test_replay_without_request_raises(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)

    with pytest.raises(ValueError):
        replay_run_sync(deps, "missing")


def test_list_capabilities_and_flows(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)
    (deps.flows_dir / "want.flow.yaml").write_text(INLINE_FLOW, encoding="utf-8")

    caps = list_capabilities(deps)
    flows = list_flows(deps)

    assert caps["actions"] == ["test.echo"]
    assert flows["flows"][0]["name"] == "inline-demo"
    assert flows["errors"] == []


def test_list_runs_limit_and_order(tmp_path: Path) -> None:
    deps = _make_deps(tmp_path)
    first = run_flow_sync(deps, flow_yaml=INLINE_FLOW)
    second = run_flow_sync(deps, flow_yaml=INLINE_FLOW)

    runs = list_runs(deps, limit=1)

    assert len(runs) == 1
    assert runs[0]["run_id"] == second["run_id"]
    assert first["run_id"] != second["run_id"]
    with pytest.raises(ValueError):
        list_runs(deps, limit=0)


def test_get_artifact_reads_truncates_and_rejects_traversal(
    tmp_path: Path,
) -> None:
    deps = _make_deps(tmp_path)
    result = run_flow_sync(deps, flow_yaml=INLINE_FLOW)
    run_dir = deps.store.artifacts_dir / result["run_id"]
    (run_dir / "note.txt").write_text("abcdef", encoding="utf-8")

    full = get_artifact(deps, result["run_id"], "note.txt")
    truncated = get_artifact(deps, result["run_id"], "note.txt", max_bytes=3)

    assert full["text"] == "abcdef"
    assert full["truncated"] is False
    assert truncated["text"] == "abc"
    assert truncated["truncated"] is True
    assert truncated["size"] == 6

    with pytest.raises(ValueError):
        get_artifact(deps, result["run_id"], "../../etc/passwd")
    with pytest.raises(ValueError):
        get_artifact(deps, "missing-run", "note.txt")
