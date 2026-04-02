# @file /backend/tests/test_hooks.py
# @brief 测试 Flow hooks（on_success / on_failure）功能
# @create 2026-03-15

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.registry import Registry
from app.runtime.models import ActionSpec, FlowSpec, HookSpec, StepSpec
from app.runtime.runner import Runner
from app.runtime.store import RunStore


def _make_registry(actions: dict = None, checks: dict = None) -> Registry:
    r = Registry()
    if actions:
        for name, fn in actions.items():
            r.register_action(name, fn)
    if checks:
        for name, fn in checks.items():
            r.register_check(name, fn)
    return r


def _make_store(tmp_path: Path) -> RunStore:
    return RunStore(artifacts_dir=tmp_path)


def _echo_action(ctx, params):
    return {"stdout": params.get("message", "ok"), "exit_code": 0}


def _fail_action(ctx, params):
    raise RuntimeError("step failed")


def _always_true(ctx, params):
    return True


def _always_false(ctx, params):
    return False


def _simple_flow(hooks: HookSpec | None = None) -> FlowSpec:
    return FlowSpec(
        version="1.0",
        name="test-flow",
        steps=[
            StepSpec(
                id="step1",
                action=ActionSpec(type="test.echo", params={"message": "hello"}),
            )
        ],
        hooks=hooks,
    )


def _failing_flow(hooks: HookSpec | None = None) -> FlowSpec:
    return FlowSpec(
        version="1.0",
        name="test-failing-flow",
        steps=[
            StepSpec(
                id="step1",
                action=ActionSpec(type="test.fail", params={}),
            )
        ],
        hooks=hooks,
    )


class TestHooks:
    def test_no_hooks_success(self, tmp_path):
        """无 hooks 时成功流程行为不变"""
        registry = _make_registry(actions={"test.echo": _echo_action})
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        result = runner.run_flow(_simple_flow(hooks=None))
        assert result.status == "success"
        assert len(result.steps) == 1

    def test_no_hooks_failure(self, tmp_path):
        """无 hooks 时失败流程行为不变"""
        registry = _make_registry(actions={"test.fail": _fail_action})
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        result = runner.run_flow(_failing_flow(hooks=None))
        assert result.status == "failed"

    def test_on_success_triggered_on_success(self, tmp_path):
        """on_success hook 在流程成功时触发"""
        hook_called = []

        def hook_action(ctx, params):
            hook_called.append(params.get("msg"))
            return {"ok": True}

        registry = _make_registry(
            actions={
                "test.echo": _echo_action,
                "test.hook": hook_action,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        hooks = HookSpec(
            on_success=[ActionSpec(type="test.hook", params={"msg": "success-hook"})],
        )
        result = runner.run_flow(_simple_flow(hooks=hooks))

        assert result.status == "success"
        assert hook_called == ["success-hook"]

    def test_on_success_not_triggered_on_failure(self, tmp_path):
        """on_success hook 在流程失败时不触发"""
        hook_called = []

        def hook_action(ctx, params):
            hook_called.append("should-not-be-called")
            return {}

        registry = _make_registry(
            actions={
                "test.fail": _fail_action,
                "test.hook": hook_action,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        hooks = HookSpec(
            on_success=[ActionSpec(type="test.hook", params={})],
        )
        result = runner.run_flow(_failing_flow(hooks=hooks))

        assert result.status == "failed"
        assert hook_called == []

    def test_on_failure_triggered_on_failure(self, tmp_path):
        """on_failure hook 在流程失败时触发"""
        hook_called = []

        def hook_action(ctx, params):
            hook_called.append(params.get("msg"))
            return {}

        registry = _make_registry(
            actions={
                "test.fail": _fail_action,
                "test.hook": hook_action,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        hooks = HookSpec(
            on_failure=[ActionSpec(type="test.hook", params={"msg": "failure-hook"})],
        )
        result = runner.run_flow(_failing_flow(hooks=hooks))

        assert result.status == "failed"
        assert hook_called == ["failure-hook"]

    def test_on_failure_not_triggered_on_success(self, tmp_path):
        """on_failure hook 在流程成功时不触发"""
        hook_called = []

        def hook_action(ctx, params):
            hook_called.append("should-not-be-called")
            return {}

        registry = _make_registry(
            actions={
                "test.echo": _echo_action,
                "test.hook": hook_action,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        hooks = HookSpec(
            on_failure=[ActionSpec(type="test.hook", params={})],
        )
        result = runner.run_flow(_simple_flow(hooks=hooks))

        assert result.status == "success"
        assert hook_called == []

    def test_hook_failure_does_not_affect_run_status(self, tmp_path):
        """hook 自身执行失败不影响主流程 status"""

        def bad_hook(ctx, params):
            raise RuntimeError("hook exploded!")

        registry = _make_registry(
            actions={
                "test.echo": _echo_action,
                "test.bad_hook": bad_hook,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        hooks = HookSpec(
            on_success=[ActionSpec(type="test.bad_hook", params={})],
        )
        result = runner.run_flow(_simple_flow(hooks=hooks))

        # 主流程仍然是 success，hook 失败被静默处理
        assert result.status == "success"

    def test_on_failure_triggered_on_foreach_failure(self, tmp_path):
        """for_each step 失败时也触发 on_failure hook"""
        hook_called = []

        def hook_action(ctx, params):
            hook_called.append("foreach-failure-hook")
            return {}

        # 创建一个会失败的 for_each flow
        call_count = [0]

        def fail_on_second(ctx, params):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise RuntimeError("second item fails")
            return {"ok": True}

        registry = _make_registry(
            actions={
                "test.fail_on_second": fail_on_second,
                "test.hook": hook_action,
            }
        )
        store = _make_store(tmp_path)
        runner = Runner(registry, store)

        flow = FlowSpec(
            version="1.0",
            name="foreach-fail-flow",
            steps=[
                StepSpec(
                    id="loop_step",
                    action=ActionSpec(type="test.fail_on_second", params={}),
                    for_each="{{vars.items}}",
                )
            ],
            hooks=HookSpec(
                on_failure=[ActionSpec(type="test.hook", params={})],
            ),
        )
        result = runner.run_flow(flow, vars={"items": ["a", "b", "c"]})

        assert result.status == "failed"
        assert hook_called == ["foreach-failure-hook"]
