# @file /backend/tests/test_session.py
# @brief 测试 RunSession:单步、续跑、状态序列化跨实例、幂等、失败与 hooks
# @create 2026-09-15

from __future__ import annotations

from pathlib import Path

from app.core.registry import Registry
from app.runtime.models import ActionSpec, FlowSpec, HookSpec, StepSpec
from app.runtime.session import RunSession
from app.runtime.storage.store import RunStore


def _make_registry(actions: dict | None = None) -> Registry:
    registry = Registry()
    for name, handler in (actions or {}).items():
        registry.register_action(name, handler)
    return registry


def _echo_action(ctx, params):
    return {"message": params.get("message", "ok")}


def _fail_action(ctx, params):
    raise RuntimeError("step failed")


def _two_step_flow() -> FlowSpec:
    return FlowSpec(
        version="1.0",
        name="session-demo",
        steps=[
            StepSpec(
                id="s1",
                action=ActionSpec(type="test.echo", params={"message": "one"}),
            ),
            StepSpec(
                id="s2",
                action=ActionSpec(type="test.echo", params={"message": "two"}),
            ),
        ],
    )


def test_step_advances_and_accumulates_results(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    session = RunSession.start(
        _make_registry({"test.echo": _echo_action}), store, _two_step_flow()
    )

    assert session.finished is False
    assert session.index == 0

    session.step()

    assert session.index == 1
    assert len(session.run.steps) == 1
    assert session.run.status == "running"

    session.run_to_completion()

    assert session.finished is True
    assert session.run.status == "success"
    assert [step.step_id for step in session.run.steps] == ["s1", "s2"]


def test_state_round_trip_resumes_in_another_store(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action})
    session = RunSession.start(
        registry, RunStore(artifacts_dir=tmp_path), _two_step_flow()
    )
    session.step()
    state = session.to_state()

    resumed = RunSession.from_state(registry, RunStore(artifacts_dir=tmp_path), state)
    resumed.run_to_completion()

    assert resumed.run.run_id == session.run.run_id
    assert resumed.run.status == "success"
    assert [step.step_id for step in resumed.run.steps] == ["s1", "s2"]
    assert resumed.run.steps[0].action_output == {"message": "one"}


def test_step_after_finish_is_noop(tmp_path: Path) -> None:
    store = RunStore(artifacts_dir=tmp_path)
    session = RunSession.start(
        _make_registry({"test.echo": _echo_action}), store, _two_step_flow()
    )
    session.run_to_completion()

    session.step()

    assert len(session.run.steps) == 2


def test_start_persists_request(tmp_path: Path) -> None:
    payload = {
        "flow_yaml": 'version: "1"',
        "input": None,
        "vars": {"dry_run": True},
    }
    store = RunStore(artifacts_dir=tmp_path)

    session = RunSession.start(
        _make_registry({"test.echo": _echo_action}),
        store,
        _two_step_flow(),
        request=payload,
    )

    assert RunStore(artifacts_dir=tmp_path).get_request(session.run.run_id) == payload


def test_failing_step_finalizes_run(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action, "test.fail": _fail_action})
    flow = FlowSpec(
        version="1.0",
        name="session-fail",
        steps=[
            StepSpec(
                id="ok",
                action=ActionSpec(type="test.echo", params={}),
            ),
            StepSpec(
                id="bad",
                action=ActionSpec(type="test.fail", params={}),
            ),
        ],
    )
    session = RunSession.start(registry, RunStore(artifacts_dir=tmp_path), flow)

    session.run_to_completion()

    assert session.run.status == "failed"
    assert session.run.error is not None and "step failed" in session.run.error
    assert [step.status for step in session.run.steps] == ["success", "failed"]


def test_hooks_recorded_by_session(tmp_path: Path) -> None:
    def hook_action(ctx, params):
        return {"hooked": True}

    registry = _make_registry({"test.echo": _echo_action, "test.hook": hook_action})
    flow = _two_step_flow()
    flow.hooks = HookSpec(on_success=[ActionSpec(type="test.hook", params={})])
    session = RunSession.start(registry, RunStore(artifacts_dir=tmp_path), flow)

    session.run_to_completion()

    assert len(session.hook_results) == 1
    assert session.hook_results[0].status == "success"
    assert session.hook_results[0].output == {"hooked": True}


def test_condition_false_marks_skipped(tmp_path: Path) -> None:
    registry = _make_registry({"test.echo": _echo_action})
    flow = FlowSpec(
        version="1.0",
        name="session-skip",
        steps=[
            StepSpec(
                id="skipped",
                condition="false",
                action=ActionSpec(type="test.echo", params={}),
            ),
        ],
    )
    session = RunSession.start(registry, RunStore(artifacts_dir=tmp_path), flow)

    session.run_to_completion()

    assert session.run.status == "success"
    assert session.run.steps[0].status == "skipped"
