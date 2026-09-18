# @file /backend/tests/test_fork.py
# @brief 测试 RunSession.fork_from_run:状态重建、失败重试、越界与 lineage
# @create 2026-09-18

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.core.registry import Registry
from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner import Runner
from app.runtime.session import RunSession
from app.runtime.storage.store import RunStore


def _make_registry(actions: dict | None = None) -> Registry:
    registry = Registry()
    for name, handler in (actions or {}).items():
        registry.register_action(name, handler)
    return registry


def _echo_action(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {"message": params.get("message", "ok")}


def _template_flow() -> FlowSpec:
    return FlowSpec(
        version="1.0",
        name="fork-demo",
        steps=[
            StepSpec(
                id="s1",
                action=ActionSpec(type="test.echo", params={"message": "seed"}),
                output_var="seed",
            ),
            StepSpec(
                id="s2",
                action=ActionSpec(
                    type="test.echo", params={"message": "{{vars.seed.message}}"}
                ),
                output_var="second",
            ),
            StepSpec(
                id="s3",
                action=ActionSpec(
                    type="test.echo",
                    params={"message": "{{steps.s2.output.message}}-tail"},
                ),
            ),
        ],
    )


def test_fork_reconstructs_state_and_matches_original(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action})
    store = RunStore(artifacts_dir=tmp_path)
    flow = _template_flow()
    request = {"flow_yaml": "irrelevant", "input": None, "vars": {}}
    original = Runner(registry, store).run_flow(
        flow, input=None, vars={}, request=request
    )

    session = RunSession.fork_from_run(
        registry,
        store,
        flow,
        source_run=original,
        request=request,
        next_step_index=2,
    )
    forked = session.run_to_completion()

    assert forked.run_id != original.run_id
    assert forked.parent_run_id == original.run_id
    assert forked.fork_step_index == 2
    assert [step.step_id for step in forked.steps[:2]] == ["s1", "s2"]
    assert (
        forked.steps[-1].action_output["message"]
        == (original.steps[-1].action_output["message"])
    )
    assert forked.steps[-1].action_output["message"] == "seed-tail"
    assert store.get_request(forked.run_id)["vars"] == {}


def test_fork_retries_failed_step(tmp_path: Path) -> None:
    attempts = {"count": 0}

    def flaky(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    registry = _make_registry({"test.echo": _echo_action, "test.flaky": flaky})
    store = RunStore(artifacts_dir=tmp_path)
    flow = FlowSpec(
        version="1.0",
        name="fork-fail",
        steps=[
            StepSpec(id="s1", action=ActionSpec(type="test.echo")),
            StepSpec(id="s2", action=ActionSpec(type="test.flaky")),
            StepSpec(id="s3", action=ActionSpec(type="test.echo")),
        ],
    )
    request = {"flow_yaml": "x", "input": None, "vars": {}}
    failed = Runner(registry, store).run_flow(flow, request=request)

    assert failed.status == "failed"

    session = RunSession.fork_from_run(
        registry,
        store,
        flow,
        source_run=failed,
        request=request,
        next_step_index=1,
    )
    session.step()

    assert session.run.steps[-1].status == "success"
    assert session.run.steps[-1].step_id == "s2"

    result = session.run_to_completion()

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == ["s1", "s2", "s3"]


def test_fork_after_failed_step_skips_it(tmp_path: Path) -> None:
    def always_fail(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("nope")

    registry = _make_registry({"test.echo": _echo_action, "test.fail": always_fail})
    store = RunStore(artifacts_dir=tmp_path)
    flow = FlowSpec(
        version="1.0",
        name="fork-skip",
        steps=[
            StepSpec(id="s1", action=ActionSpec(type="test.echo")),
            StepSpec(id="s2", action=ActionSpec(type="test.fail")),
            StepSpec(id="s3", action=ActionSpec(type="test.echo")),
        ],
    )
    request = {"flow_yaml": "x", "input": None, "vars": {}}
    failed = Runner(registry, store).run_flow(flow, request=request)

    session = RunSession.fork_from_run(
        registry,
        store,
        flow,
        source_run=failed,
        request=request,
        next_step_index=2,
    )
    result = session.run_to_completion()

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == ["s1", "s2", "s3"]
    assert result.steps[1].status == "failed"
    assert result.steps[2].status == "success"


def test_fork_index_out_of_range_raises(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action})
    store = RunStore(artifacts_dir=tmp_path)
    flow = _template_flow()
    source = Runner(registry, store).run_flow(flow)

    for bad in (-1, len(source.steps) + 1):
        with pytest.raises(ValueError):
            RunSession.fork_from_run(
                registry,
                store,
                flow,
                source_run=source,
                request=None,
                next_step_index=bad,
            )


def test_fork_from_zero_starts_fresh(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action})
    store = RunStore(artifacts_dir=tmp_path)
    flow = _template_flow()
    source = Runner(registry, store).run_flow(flow)

    session = RunSession.fork_from_run(
        registry,
        store,
        flow,
        source_run=source,
        request=None,
        next_step_index=0,
    )

    assert session.index == 0
    assert session.run.steps == []
    assert session.run_to_completion().status == "success"
