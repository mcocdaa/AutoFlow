# @file /backend/tests/test_control_flow.py
# @brief AutoFlow Phase 2 鎺у埗娴佸寮洪泦鎴愭祴璇?# @create 2026-03-14

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner.runner import Runner, evaluate_condition, resolve_templates
from app.plugin.registry import ActionContext, Registry
from app.runtime.storage.store import RunStore


class TestConditionEvaluation:
    """鏉′欢琛ㄨ揪寮忚瘎浼版祴璇?""

    def test_evaluate_condition_true_false(self) -> None:
        """true/false 甯冨皵鍊?""
        assert evaluate_condition("true") is True
        assert evaluate_condition("false") is False
        assert evaluate_condition("TRUE") is True
        assert evaluate_condition("FALSE") is False

    def test_evaluate_condition_string_equality(self) -> None:
        """瀛楃涓茬浉绛夋瘮杈?""
        assert evaluate_condition('"hello" == "hello"') is True
        assert evaluate_condition("'hello' == 'hello'") is True
        assert evaluate_condition('"hello" != "world"') is True
        assert evaluate_condition('"hello" == "world"') is False
        assert evaluate_condition('"hello" != "hello"') is False

    def test_evaluate_condition_number_comparison(self) -> None:
        """鏁板瓧姣旇緝"""
        assert evaluate_condition("5 > 3") is True
        assert evaluate_condition("5 < 3") is False
        assert evaluate_condition("5 >= 5") is True
        assert evaluate_condition("5 <= 5") is True
        assert evaluate_condition("10.5 > 10.0") is True
        assert evaluate_condition("-1 < 0") is True

    def test_evaluate_condition_invalid_returns_false(self) -> None:
        """鏃犳硶瑙ｆ瀽鐨勮〃杈惧紡杩斿洖 False"""
        assert evaluate_condition("some random text") is False
        assert evaluate_condition("") is False
        assert evaluate_condition("===") is False


class TestConditionalStepExecution:
    """鏉′欢姝ラ鎵ц娴嬭瘯"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()
        # 娉ㄥ唽涓€涓畝鍗曠殑 action锛岃繑鍥炲浐瀹氬€?        def echo_action(context: ActionContext, params: dict[str, Any]) -> Any:
            return {"step_id": context.step_id, "params": params}
        reg.register_action("test.echo", echo_action)
        # 娉ㄥ唽涓€涓?always_true check
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
        """condition="true" 鏃舵甯告墽琛?""
        flow = FlowSpec(
            version="1",
            name="True Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="true"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "success"
        assert run.steps[0].step_id == "step1"

    def test_step_with_false_condition(self, runner: Runner) -> None:
        """condition="false" 鏃惰烦杩囷紙status=skipped锛?""
        flow = FlowSpec(
            version="1",
            name="False Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="false"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "skipped"
        assert run.steps[0].step_id == "step1"
        assert run.steps[0].action_output is None

    def test_step_condition_with_variable(self, runner: Runner) -> None:
        """condition 寮曠敤 {{vars.flag}}"""
        flow = FlowSpec(
            version="1",
            name="Variable Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.echo", params={"message": "hello"}),
                    condition="{{vars.flag}}"
                ),
            ]
        )
        # vars.flag 涓?"true" 鏃跺簲鎵ц
        run = runner.run_flow(flow, input=None, vars={"flag": "true"})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "success"
        # vars.flag 涓?"false" 鏃跺簲璺宠繃
        run = runner.run_flow(flow, input=None, vars={"flag": "false"})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "skipped"


class TestForEachLoop:
    """for 寰幆娴嬭瘯"""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()
        # action 杩斿洖褰撳墠杩唬椤?        def foreach_action(context: ActionContext, params: dict[str, Any]) -> Any:
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

    @pytest.mark.xfail(reason="for_each 鍔熻兘灏氭湭鍦?runner 涓疄鐜?)
    def test_foreach_iterates_list(self, runner: Runner) -> None:
        """閬嶅巻 ["x","y","z"]"""
        flow = FlowSpec(
            version="1",
            name="ForEach List Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.foreach", params={}),
                    for_each="{{vars.items}}",
                    for_item_var="item"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={"items": ["x", "y", "z"]})
        assert run.status == "success"
        assert len(run.steps) == 1
        step_result = run.steps[0]
        # 搴旇褰曡凯浠ｇ粨鏋?        assert step_result.iterations is not None
        assert len(step_result.iterations) == 3
        # 姣忎釜杩唬搴旀湁鐩稿簲鐨勮緭鍑?        # 鐢变簬 runner 鏈疄鐜帮紝杩欓噷鍙槸棰勬湡澶辫触鍗犱綅

    @pytest.mark.xfail(reason="for_each 鍔熻兘灏氭湭鍦?runner 涓疄鐜?)
    def test_foreach_empty_list(self, runner: Runner) -> None:
        """绌哄垪琛ㄦ椂璺宠繃"""
        flow = FlowSpec(
            version="1",
            name="ForEach Empty List Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.foreach", params={}),
                    for_each="{{vars.items}}",
                    for_item_var="item"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={"items": []})
        assert run.status == "success"
        assert len(run.steps) == 1
        assert run.steps[0].status == "skipped"
        assert run.steps[0].iterations == []

    @pytest.mark.xfail(reason="for_each 鍔熻兘灏氭湭鍦?runner 涓疄鐜?)
    def test_foreach_with_index(self, runner: Runner) -> None:
        """楠岃瘉 {{index}} 鍙敤"""
        flow = FlowSpec(
            version="1",
            name="ForEach With Index Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.foreach", params={"index": "{{index}}"}),
                    for_each="{{vars.items}}",
                    for_item_var="item"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={"items": ["a", "b"]})
        assert run.status == "success"
        # 鏈熸湜杩唬涓?index 姝ｇ‘浼犻€?        # 鐢变簬 runner 鏈疄鐜帮紝杩欓噷鍙槸棰勬湡澶辫触鍗犱綅


class TestCombinedControlFlow:
    """缁勫悎鎺у埗娴佹祴璇?""

    @pytest.fixture
    def registry(self) -> Registry:
        reg = Registry()
        # action 杩斿洖褰撳墠鍙橀噺鐘舵€?        def state_action(context: ActionContext, params: dict[str, Any]) -> Any:
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

    @pytest.mark.xfail(reason="for_each 鍔熻兘灏氭湭鍦?runner 涓疄鐜?)
    def test_condition_inside_foreach(self, runner: Runner) -> None:
        """寰幆鍐呭甫鏉′欢鍒ゆ柇"""
        flow = FlowSpec(
            version="1",
            name="Condition Inside ForEach Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.state", params={}),
                    for_each="{{vars.numbers}}",
                    for_item_var="num",
                    condition="{{num}} > 2"
                ),
            ]
        )
        run = runner.run_flow(flow, input=None, vars={"numbers": [1, 2, 3, 4]})
        assert run.status == "success"
        # 鏈熸湜鍙湁 3 鍜?4 琚鐞?        # 鐢变簬 runner 鏈疄鐜帮紝杩欓噷鍙槸棰勬湡澶辫触鍗犱綅

    def test_variable_passing_with_condition(self, runner: Runner) -> None:
        """鏉′欢鍒嗘敮 + 鍙橀噺浼犻€?""
        flow = FlowSpec(
            version="1",
            name="Variable Passing With Condition Test",
            steps=[
                StepSpec(
                    id="step1",
                    action=ActionSpec(type="test.state", params={"set": "first"}),
                    output_var="var1",
                    condition="{{vars.run_first}}"
                ),
                StepSpec(
                    id="step2",
                    action=ActionSpec(type="test.state", params={"received": "{{vars.var1}}"}),
                ),
            ]
        )
        # 褰?run_first 涓?true 鏃讹紝step1 鎵ц锛寁ar1 琚缃?        run = runner.run_flow(flow, input=None, vars={"run_first": "true"})
        assert run.status == "success"
        assert len(run.steps) == 2
        assert run.steps[0].status == "success"
        assert run.steps[1].status == "success"
        # step2 搴旇兘鎺ユ敹鍒?var1
        # 娉ㄦ剰锛歰utput_var 鍔熻兘鍙兘灏氭湭瀹炵幇锛屼絾杩欓噷鍋囪宸插疄鐜?        # 濡傛灉鏈疄鐜帮紝娴嬭瘯浼氬け璐?
        # 褰?run_first 涓?false 鏃讹紝step1 璺宠繃锛寁ar1 鏈缃?        run = runner.run_flow(flow, input=None, vars={"run_first": "false"})
        assert run.status == "success"
        assert len(run.steps) == 2
        assert run.steps[0].status == "skipped"
        assert run.steps[1].status == "success"
        # step2 鐨?received 鍙傛暟鍙兘鏃犳硶瑙ｆ瀽锛屼絾 runner 搴旇兘澶勭悊缂哄け鍙橀噺


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
