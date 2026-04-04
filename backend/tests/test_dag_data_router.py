# @file /backend/tests/test_dag_data_router.py
# @brief 测试 DAG 数据路由、分发、条件评估
# @create 2026-04-01

from __future__ import annotations

from datetime import datetime

import pytest

from app.runtime.dag_models import (
    DAGWorkflow,
    Edge,
    InputPort,
    OutputPort,
    RetrySpec,
)
from app.runtime.data_router import ConditionEvaluator, DataRouter
from app.runtime.execution_state import ExecutionState
from app.runtime.nodes import EndNode, PassNode, StartNode


def create_router_test_dag():
    """创建用于路由测试的 DAG"""
    start_node = StartNode(
        id="start",
        name="Start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        outputs=[
            OutputPort(id="output", name="Output", type="any", required=True),
            OutputPort(
                id="conditional_output",
                name="Conditional Output",
                type="any",
                required=True,
                condition="data > 0",
            ),
        ],
    )
    pass1_node = PassNode(
        id="pass1",
        name="Pass 1",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass2_node = PassNode(
        id="pass2",
        name="Pass 2",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[
            InputPort(id="input1", name="Input 1", type="any", required=True),
            InputPort(
                id="input2",
                name="Input 2",
                type="any",
                required=False,
                default="default",
            ),
        ],
    )
    workflow = DAGWorkflow(
        name="Router Test DAG",
        nodes={
            "start": start_node,
            "pass1": pass1_node,
            "pass2": pass2_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.output", target="pass1.input"),
            Edge(id="e2", source="pass1.output", target="end.input1"),
            Edge(id="e3", source="start.conditional_output", target="pass2.input"),
            Edge(id="e4", source="pass2.output", target="end.input2"),
        ],
    )
    return workflow


class TestConditionEvaluator:
    def test_evaluate_none_condition_returns_true(self):
        """测试 None 条件返回 True"""
        result = ConditionEvaluator.evaluate(None, "data", {})
        assert result is True

    def test_evaluate_simple_true_condition(self):
        """测试简单的真条件"""
        result = ConditionEvaluator.evaluate("data > 5", 10, {})
        assert result is True

    def test_evaluate_simple_false_condition(self):
        """测试简单的假条件"""
        result = ConditionEvaluator.evaluate("data > 5", 3, {})
        assert result is False

    def test_evaluate_with_variables(self):
        """测试带变量的条件"""
        variables = {"threshold": 10}
        result = ConditionEvaluator.evaluate(
            "data > variables.threshold", 15, variables
        )
        assert result is True

    def test_evaluate_complex_expression(self):
        """测试复杂表达式"""
        variables = {"min": 5, "max": 20}
        result = ConditionEvaluator.evaluate(
            "data > variables.min and data < variables.max", 10, variables
        )
        assert result is True

    def test_evaluate_invalid_condition_returns_false(self):
        """测试无效条件返回 False"""
        result = ConditionEvaluator.evaluate("invalid syntax", 10, {})
        assert result is False

    def test_evaluate_boolean_constants(self):
        """测试布尔常量"""
        assert ConditionEvaluator.evaluate("True", None, {}) is True
        assert ConditionEvaluator.evaluate("False", None, {}) is False
        assert ConditionEvaluator.evaluate("None", None, {}) is False


class TestDataRouterCreation:
    def test_router_creation(self):
        """测试 DataRouter 创建"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)
        assert router.workflow is workflow
        assert router.state is state
        assert router.condition_evaluator is not None


class TestCreateMessage:
    def test_create_success_message(self):
        """测试创建成功消息"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        message = router.create_message(
            success=True,
            data="test data",
            error=None,
            source_node_id="node1",
            source_port_id="port1",
        )

        assert message.success is True
        assert message.data == "test data"
        assert message.error is None
        assert message.metadata.source_node == "node1"
        assert message.metadata.source_port == "port1"

    def test_create_error_message(self):
        """测试创建错误消息"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        message = router.create_message(
            success=False,
            data=None,
            error="Something went wrong",
            source_node_id="node1",
            source_port_id="port1",
        )

        assert message.success is False
        assert message.data is None
        assert message.error == "Something went wrong"


class TestDistributeOutputs:
    def test_distribute_outputs_single_port(self):
        """测试单个端口输出分发"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        node = workflow.nodes["pass1"]
        outputs = {"output": "test value"}

        router.distribute_outputs(node, outputs)

        assert "end.input1" in state.available_inputs
        assert state.available_inputs["end.input1"] == "test value"

    def test_distribute_outputs_multiple_ports(self):
        """测试多个端口输出分发"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        node = workflow.nodes["start"]
        outputs = {"output": "value1", "conditional_output": 5}

        router.distribute_outputs(node, outputs)

        assert "pass1.input" in state.available_inputs
        assert state.available_inputs["pass1.input"] == "value1"
        assert "pass2.input" in state.available_inputs
        assert state.available_inputs["pass2.input"] == 5


class TestConditionalDistribution:
    def test_conditional_passes(self):
        """测试条件通过时的分发"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        node = workflow.nodes["start"]
        outputs = {"conditional_output": 10}  # 10 > 0，条件通过

        router.distribute_outputs(node, outputs)

        assert "pass2.input" in state.available_inputs
        assert state.available_inputs["pass2.input"] == 10

    def test_conditional_fails(self):
        """测试条件失败时不分发"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        node = workflow.nodes["start"]
        outputs = {"conditional_output": -5}  # -5 <= 0，条件失败

        router.distribute_outputs(node, outputs)

        assert "pass2.input" not in state.available_inputs

    def test_conditional_with_variables(self):
        """测试带变量的条件分发"""
        workflow = DAGWorkflow(
            name="Variable Condition Test",
            nodes={},
            edges=[],
        )
        state = ExecutionState()
        state.variables.set("threshold", 50)
        router = DataRouter(workflow, state)

        # 创建临时节点带条件输出
        node = PassNode(
            id="test",
            name="Test",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="any",
                    required=True,
                    condition="data > variables.threshold",
                )
            ],
        )

        # 手动添加节点到工作流
        workflow.nodes["test"] = node

        # 添加边
        edge = Edge(id="e1", source="test.output", target="end.input")
        workflow.edges.append(edge)

        # 创建目标节点
        end_node = EndNode(
            id="end",
            name="End",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        )
        workflow.nodes["end"] = end_node

        router.distribute_outputs(node, {"output": 100})

        assert "end.input" in state.available_inputs
        assert state.available_inputs["end.input"] == 100


class TestErrorDistribution:
    def test_error_port_distribution(self):
        """测试错误端口分发"""
        workflow = DAGWorkflow(
            name="Error Distribution Test",
            nodes={},
            edges=[],
        )
        state = ExecutionState()
        router = DataRouter(workflow, state)

        # 创建节点
        node = PassNode(
            id="test",
            name="Test",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[],
        )
        workflow.nodes["test"] = node

        # 添加错误端口的边
        edge = Edge(id="e1", source="test.error", target="error_handler.input")
        workflow.edges.append(edge)

        # 创建错误处理节点
        error_handler = PassNode(
            id="error_handler",
            name="Error Handler",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[InputPort(id="input", name="Input", type="any", required=True)],
            outputs=[],
        )
        workflow.nodes["error_handler"] = error_handler

        # 标记节点为失败
        record = state.history.get_record("test")
        record.status = "failed"
        record.error = "Test error message"

        router.distribute_outputs(node, {})

        assert "error_handler.input" in state.available_inputs
        assert state.available_inputs["error_handler.input"] == "Test error message"


class TestGetAvailableInputs:
    def test_get_available_inputs_for_node(self):
        """测试获取节点可用输入"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        state.available_inputs["end.input1"] = "value1"
        state.available_inputs["end.input2"] = "value2"

        node = workflow.nodes["end"]
        inputs = router.get_available_inputs_for_node(node)

        assert inputs == {"input1": "value1", "input2": "value2"}

    def test_get_available_inputs_with_defaults(self):
        """测试获取带默认值的可用输入"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        state.available_inputs["end.input1"] = "value1"

        node = workflow.nodes["end"]
        inputs = router.get_available_inputs_for_node(node)

        assert inputs == {"input1": "value1", "input2": "default"}


class TestHasRequiredInputs:
    def test_has_required_inputs_true(self):
        """测试所有必需输入都可用"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        state.available_inputs["end.input1"] = "value1"

        node = workflow.nodes["end"]
        has_required = router.has_required_inputs(node)

        assert has_required is True

    def test_has_required_inputs_false(self):
        """测试缺少必需输入"""
        workflow = create_router_test_dag()
        state = ExecutionState()
        router = DataRouter(workflow, state)

        node = workflow.nodes["end"]
        has_required = router.has_required_inputs(node)

        assert has_required is False
