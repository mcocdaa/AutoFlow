# @file /backend/tests/test_dag_nodes.py
# @brief 测试 DAG 基础节点类型（StartNode、EndNode、ActionNode、PassNode）
# @create 2026-04-01

from __future__ import annotations

import pytest

from app.runtime.dag_models import (
    BaseNode,
    InputPort,
    OutputPort,
    RetrySpec,
)
from app.runtime.nodes import ActionNode, EndNode, PassNode, StartNode


class TestStartNode:
    def test_start_node_creation(self):
        """测试 StartNode 创建"""
        node = StartNode(
            id="start_1",
            name="Start",
            type="start",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={"position": {"x": 100, "y": 100}},
            inputs=[],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="any",
                    required=True,
                )
            ],
        )

        assert node.id == "start_1"
        assert node.name == "Start"
        assert node.type == "start"
        assert len(node.inputs) == 0
        assert len(node.outputs) == 1

    def test_start_node_execute(self):
        """测试 StartNode 执行"""
        node = StartNode(
            id="start_1",
            name="Start",
            type="start",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[
                OutputPort(
                    id="output1",
                    name="Output 1",
                    type="string",
                    required=True,
                ),
                OutputPort(
                    id="output2",
                    name="Output 2",
                    type="number",
                    required=True,
                    default=42,
                ),
            ],
        )

        inputs = {"output1": "hello"}
        outputs = node.execute(inputs)

        assert outputs["output1"] == "hello"
        assert outputs["output2"] == 42


class TestEndNode:
    def test_end_node_creation(self):
        """测试 EndNode 创建"""
        node = EndNode(
            id="end_1",
            name="End",
            type="end",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={"position": {"x": 500, "y": 100}},
            inputs=[
                InputPort(
                    id="input",
                    name="Input",
                    type="any",
                    required=True,
                )
            ],
            outputs=[],
        )

        assert node.id == "end_1"
        assert node.name == "End"
        assert node.type == "end"
        assert len(node.inputs) == 1
        assert len(node.outputs) == 0

    def test_end_node_execute(self):
        """测试 EndNode 执行"""
        node = EndNode(
            id="end_1",
            name="End",
            type="end",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(
                    id="input1",
                    name="Input 1",
                    type="string",
                    required=True,
                ),
                InputPort(
                    id="input2",
                    name="Input 2",
                    type="number",
                    required=True,
                ),
            ],
            outputs=[],
        )

        inputs = {"input1": "result", "input2": 100}
        outputs = node.execute(inputs)

        assert outputs == inputs


class TestActionNode:
    def test_action_node_creation(self):
        """测试 ActionNode 创建"""
        node = ActionNode(
            id="action_1",
            name="Log Message",
            action_type="log",
            type="action",
            retry=RetrySpec(attempts=2, backoff_seconds=1),
            config={"action_type": "log"},
            metadata={"position": {"x": 300, "y": 100}},
            inputs=[
                InputPort(
                    id="message",
                    name="Message",
                    type="string",
                    required=True,
                )
            ],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="any",
                    required=True,
                )
            ],
        )

        assert node.id == "action_1"
        assert node.name == "Log Message"
        assert node.type == "action"
        assert node.config["action_type"] == "log"
        assert node.retry.attempts == 2

    def test_action_node_execute_with_handler(self):
        """测试 ActionNode 执行（带 handler）"""
        node = ActionNode(
            id="action_1",
            name="Test Action",
            action_type="test",
            type="action",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={"action_type": "test"},
            metadata={},
            inputs=[
                InputPort(
                    id="input",
                    name="Input",
                    type="number",
                    required=True,
                )
            ],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="number",
                    required=True,
                )
            ],
        )

        def test_handler(inputs: dict, **kwargs):
            return inputs["input"] * 2

        inputs = {"input": 5}
        outputs = node.execute(inputs, action_handler=test_handler)

        assert outputs["output"] == 10


class TestPassNode:
    def test_pass_node_creation(self):
        """测试 PassNode 创建"""
        node = PassNode(
            id="pass_1",
            name="Pass Through",
            type="pass",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={"position": {"x": 300, "y": 200}},
            inputs=[
                InputPort(
                    id="input",
                    name="Input",
                    type="any",
                    required=True,
                )
            ],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="any",
                    required=True,
                )
            ],
        )

        assert node.id == "pass_1"
        assert node.name == "Pass Through"
        assert node.type == "pass"

    def test_pass_node_execute_passthrough(self):
        """测试 PassNode 直接透传"""
        node = PassNode(
            id="pass_1",
            name="Pass Through",
            type="pass",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(
                    id="input1",
                    name="Input 1",
                    type="string",
                    required=True,
                ),
                InputPort(
                    id="input2",
                    name="Input 2",
                    type="number",
                    required=True,
                ),
            ],
            outputs=[
                OutputPort(
                    id="input1",
                    name="Output 1",
                    type="string",
                    required=True,
                ),
                OutputPort(
                    id="input2",
                    name="Output 2",
                    type="number",
                    required=True,
                ),
            ],
        )

        inputs = {"input1": "test", "input2": 123}
        outputs = node.execute(inputs)

        assert outputs["input1"] == "test"
        assert outputs["input2"] == 123

    def test_pass_node_execute_with_transform(self):
        """测试 PassNode 带数据转换"""
        node = PassNode(
            id="pass_1",
            name="Pass Through",
            type="pass",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(
                    id="input",
                    name="Input",
                    type="string",
                    required=True,
                )
            ],
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="string",
                    required=True,
                )
            ],
        )

        inputs = {"input": "hello"}
        outputs = node.execute(inputs)

        assert outputs["output"] == "hello"
