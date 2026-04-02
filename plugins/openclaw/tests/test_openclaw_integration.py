# @file /plugins/openclaw/tests/test_openclaw_integration.py
# @brief AutoFlow × OpenClaw 集成 Phase 1 测试用例
# @create 2026-03-14

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call

import pytest
from app.plugin.registry import ActionContext, Registry
from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner import Runner
from app.runtime.storage import RunStore
from app.runtime.utils import resolve_templates


class TestResolveTemplates:
    """变量模板解析测试"""

    def test_resolve_simple_var(self) -> None:
        """{{vars.name}} 替换为实际值"""
        obj = {"greeting": "Hello {{vars.name}}!"}
        context = {"vars": {"name": "Alice"}}
        result = resolve_templates(obj, context)
        assert result == {"greeting": "Hello Alice!"}

    def test_resolve_step_output(self) -> None:
        """{{steps.step1.output}} 替换为 step 输出"""
        obj = {"data": "Step output: {{steps.step1.output}}"}
        context = {"steps": {"step1": {"result": 42}}}
        result = resolve_templates(obj, context)
        expected = 'Step output: {"result": 42}'
        assert result == {"data": expected}

    def test_resolve_nested(self) -> None:
        """嵌套 dict/list 中的模板也能替换"""
        obj = {
            "list": ["{{vars.a}}", {"deep": "{{vars.b}}"}],
            "dict": {"nested": "{{vars.c}}"},
        }
        context = {"vars": {"a": 1, "b": 2, "c": 3}}
        result = resolve_templates(obj, context)
        assert result == {"list": [1, {"deep": 2}], "dict": {"nested": 3}}

    def test_resolve_no_match(self) -> None:
        """无匹配的模板保持原样不报错"""
        obj = {"text": "Hello {{unknown}}"}
        context = {"vars": {"foo": "bar"}}
        result = resolve_templates(obj, context)
        assert result == {"text": "Hello {{unknown}}"}

    def test_resolve_input(self) -> None:
        """{{input}} 替换"""
        obj = {"message": "Input is {{input}}"}
        context = {"input": {"key": "value"}}
        result = resolve_templates(obj, context)
        expected = 'Input is {"key": "value"}'
        assert result == {"message": expected}


class TestVariablePassingEndToEnd:
    """变量传递端到端测试"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()

        def echo_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return {"params": params, "step_id": context.step_id}

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

    def test_flow_with_variable_passing(self, runner: Runner) -> None:
        """多步 Flow，step A 输出传给 step B"""
        flow = FlowSpec(
            version="1",
            name="Variable Passing Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "first"}),
                    output_var="first_output",
                ),
                StepSpec(
                    id="step2",
                    action=ActionSpec(
                        type="test.echo", params={"previous": "{{steps.step1.output}}"}
                    ),
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        assert len(run.steps) == 2
        assert run.steps[0].status == "success"
        assert run.steps[1].status == "success"

        step1_output = run.steps[0].action_output
        assert step1_output is not None
        assert step1_output["params"]["message"] == "first"

        step2_output = run.steps[1].action_output
        assert step2_output is not None
        previous_param = step2_output["params"]["previous"]
        assert previous_param == step1_output

    def test_vars_reference(self, runner: Runner) -> None:
        """引用 runtime_vars 中的变量"""
        flow = FlowSpec(
            version="1",
            name="Vars Reference Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(
                        type="test.echo", params={"value": "{{vars.initial}}"}
                    ),
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={"initial": 123})
        assert run.status == "success"
        step_output = run.steps[0].action_output
        assert step_output["params"]["value"] == 123


class TestOutputVar:
    """output_var 测试"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()

        def param_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return params

        reg.register_action("test.param", param_action)
        reg.register_check("test.always_true", lambda ctx, params: True)
        return reg

    @pytest.fixture
    def store(self) -> RunStore:
        artifacts_dir = Path(tempfile.mkdtemp())
        return RunStore(artifacts_dir)

    @pytest.fixture
    def runner(self, registry: Registry, store: RunStore) -> Runner:
        return Runner(registry, store)

    @pytest.mark.xfail(reason="output_var 功能尚未在 runner 中实现")
    def test_output_var_stores_to_vars(self, runner: Runner) -> None:
        """设置 output_var 后 action_output 存入 runtime_vars"""
        flow = FlowSpec(
            version="1",
            name="Output Var Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.param", params={"data": "value1"}),
                    output_var="stored",
                ),
                StepSpec(
                    id="step2",
                    action=ActionSpec(
                        type="test.param", params={"received": "{{vars.stored}}"}
                    ),
                ),
            ],
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        step1_output = run.steps[0].action_output
        assert step1_output == {"data": "value1"}
        step2_output = run.steps[1].action_output
        assert step2_output["received"] == {"data": "value1"}
