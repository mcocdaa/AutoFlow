# @file /backend/tests/test_control_flow.py
# @brief AutoFlow Phase 2 控制流增强集成测试
# @create 2026-03-14

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from app.core.registry import ActionContext, Registry
from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner import Runner
from app.runtime.store import RunStore
from app.runtime.utils import evaluate_condition, resolve_templates


class TestConditionEvaluation:
    """条件表达式评估测试"""

    def test_evaluate_condition_true_false(self) -> None:
        """true/false 布尔值"""
        assert evaluate_condition("true") is True
        assert evaluate_condition("false") is False
        assert evaluate_condition("TRUE") is True
        assert evaluate_condition("FALSE") is False

    def test_evaluate_condition_string_equality(self) -> None:
        """字符串相等比较"""
        assert evaluate_condition('"hello" == "hello"') is True
        assert evaluate_condition("'hello' == 'hello'") is True
        assert evaluate_condition('"hello" != "world"') is True
        assert evaluate_condition('"hello" == "world"') is False
        assert evaluate_condition('"hello" != "hello"') is False

    def test_evaluate_condition_number_comparison(self) -> None:
        """数字比较"""
        assert evaluate_condition("5 > 3") is True
        assert evaluate_condition("5 < 3") is False
        assert evaluate_condition("5 >= 5") is True
        assert evaluate_condition("5 <= 5") is True
        assert evaluate_condition("10.5 > 10.0") is True
        assert evaluate_condition("-1 < 0") is True

    def test_evaluate_condition_invalid_returns_false(self) -> None:
        """无法解析的表达式返回 False"""
        assert evaluate_condition("some random text") is False
        assert evaluate_condition("") is False
        assert evaluate_condition("===") is False


class TestConditionalStepExecution:
    """条件步骤执行测试"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()

        def echo_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return {"step_id": context.step_id, "params": params}

        reg.register_action("test.echo", echo_action)
        reg.register_check("test.always_true", lambda ctx, params: True)
        return reg

    @pytest.fixture
    def store(self) -> RunStore:
        artifacts_dir = Path(tempfile.mkdtemp())
        return RunStore(artifacts_dir)

    @pytest.fixture
    def runner(self, registry: Registry, store: RunStore) -> Runner:
        return Runner(registry, store)

    def test_step_with_true_condition(self, runner: Runner) -> None:
        """condition="true" 时正常执行"""
        flow = FlowSpec(
            version="1",
            name="True Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="true",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "success"
        assert run.steps[0].step_id == "step1"

    def test_step_with_false_condition(self, runner: Runner) -> None:
        """condition="false" 时跳过（status=skipped）"""
        flow = FlowSpec(
            version="1",
            name="False Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="false",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "skipped"
        assert run.steps[0].step_id == "step1"
        assert run.steps[0].action_output is None

    def test_step_condition_with_variable(self, runner: Runner) -> None:
        """condition 引用 {{vars.flag}}"""
        flow = FlowSpec(
            version="1",
            name="Variable Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="{{vars.flag}}",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"flag": "true"})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "success"
        run = runner.run_flow(flow, input=None, vars={"flag": "false"})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "skipped"


class TestForEachLoop:
    """for 循环测试"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()

        def foreach_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return {"item": params.get("item"), "index": params.get("index")}

        reg.register_action("test.foreach", foreach_action)
        reg.register_check("test.always_true", lambda ctx, params: True)
        return reg

    @pytest.fixture
    def store(self) -> RunStore:
        artifacts_dir = Path(tempfile.mkdtemp())
        return RunStore(artifacts_dir)

    @pytest.fixture
    def runner(self, registry: Registry, store: RunStore) -> Runner:
        return Runner(registry, store)

    def test_foreach_iterates_list(self, runner: Runner) -> None:
        """遍历 ["x","y","z"]"""
        flow = FlowSpec(
            version="1",
            name="ForEach List Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.foreach", params={}),
                    for_each="{{vars.items}}",
                    for_item_var="item",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"items": ["x", "y", "z"]})
        assert run.status == "success"
        assert len(run.steps) == 1
        step_result = run.steps[0]
        assert step_result.iterations is not None
        assert len(step_result.iterations) == 3
        assert step_result.iterations[0]["item"] == "x"
        assert step_result.iterations[1]["item"] == "y"
        assert step_result.iterations[2]["item"] == "z"

    def test_foreach_empty_list(self, runner: Runner) -> None:
        """空列表时执行成功，iterations 为空"""
        flow = FlowSpec(
            version="1",
            name="ForEach Empty List Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.foreach", params={}),
                    for_each="{{vars.items}}",
                    for_item_var="item",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"items": []})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "success"
        assert run.steps[0].iterations == []

    def test_foreach_with_index(self, runner: Runner) -> None:
        """验证 {{index}} 可用"""
        flow = FlowSpec(
            version="1",
            name="ForEach With Index Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(
                        type="test.foreach", params={"index": "{{index}}"}
                    ),
                    for_each="{{vars.items}}",
                    for_item_var="item",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"items": ["a", "b"]})
        assert run.status == "success"
        assert run.steps[0].iterations is not None
        assert len(run.steps[0].iterations) == 2
        assert run.steps[0].iterations[0]["item"] == "a"
        assert run.steps[0].iterations[1]["item"] == "b"


class TestCombinedControlFlow:
    """组合控制流测试"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()

        def state_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return {"step_id": context.step_id, "vars": dict(context.vars)}

        reg.register_action("test.state", state_action)
        reg.register_check("test.always_true", lambda ctx, params: True)
        return reg

    @pytest.fixture
    def store(self) -> RunStore:
        artifacts_dir = Path(tempfile.mkdtemp())
        return RunStore(artifacts_dir)

    @pytest.fixture
    def runner(self, registry: Registry, store: RunStore) -> Runner:
        return Runner(registry, store)

    def test_condition_inside_foreach(self, runner: Runner) -> None:
        """condition 应用在整个步骤级别"""
        flow = FlowSpec(
            version="1",
            name="Condition Inside ForEach Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.state", params={}),
                    for_each="{{vars.numbers}}",
                    for_item_var="num",
                    condition="true",
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"numbers": [1, 2, 3, 4]})
        assert run.status == "success"
        assert run.steps[0].iterations is not None
        assert len(run.steps[0].iterations) == 4

    def test_variable_passing_with_condition(self, runner: Runner) -> None:
        """条件分支 + 变量传递"""
        flow = FlowSpec(
            version="1",
            name="Variable Passing With Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.state", params={"set": "first"}),
                    output_var="var1",
                    condition="{{vars.run_first}}",
                ),
                StepSpec(
                    id="step2",
                    action=ActionSpec(
                        type="test.state", params={"received": "{{vars.var1}}"}
                    ),
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"run_first": "true"})
        assert run.status == "success"
        assert len(run.steps) == 2
        assert run.steps[0].status == "success"
        assert run.steps[1].status == "success"
        run = runner.run_flow(flow, input=None, vars={"run_first": "false"})
        assert run.status == "success"
        assert len(run.steps) == 2
        assert run.steps[0].status == "skipped"
        assert run.steps[1].status == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
