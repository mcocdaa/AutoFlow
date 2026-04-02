# @file /backend/tests/test_dag_executor.py
# @brief 测试 DAG 节点执行器、状态管理、输入收集、重试逻辑、错误处理
# @create 2026-04-01

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.runtime.actions import ActionRegistry
from app.runtime.dag_models import (
    InputPort,
    OutputPort,
    RetrySpec,
)
from app.runtime.execution_state import ExecutionState, NodeStatus
from app.runtime.executor import NodeExecutor
from app.runtime.nodes import ActionNode, EndNode, PassNode, StartNode


class TestNodeExecutorCreation:
    def test_executor_creation(self):
        state = ExecutionState()
        executor = NodeExecutor(state)
        assert executor.state is state
        assert executor.action_registry is not None

    def test_executor_with_custom_registry(self):
        state = ExecutionState()
        registry = ActionRegistry()
        executor = NodeExecutor(state, action_registry=registry)
        assert executor.action_registry is registry


class TestInputCollection:
    def test_collect_inputs_from_available_inputs(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="test_node",
            name="Test Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(id="input1", name="Input 1", type="any", required=True),
                InputPort(id="input2", name="Input 2", type="any", required=True),
            ],
            outputs=[],
        )

        state.available_inputs["test_node.input1"] = "value1"
        state.available_inputs["test_node.input2"] = "value2"

        inputs = executor.collect_inputs(node)
        assert inputs == {"input1": "value1", "input2": "value2"}

    def test_collect_inputs_with_defaults(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="test_node",
            name="Test Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(
                    id="input1",
                    name="Input 1",
                    type="any",
                    required=True,
                    default="default1",
                ),
                InputPort(
                    id="input2",
                    name="Input 2",
                    type="any",
                    required=True,
                    default="default2",
                ),
            ],
            outputs=[],
        )

        inputs = executor.collect_inputs(node)
        assert inputs == {"input1": "default1", "input2": "default2"}

    def test_collect_inputs_mixed(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="test_node",
            name="Test Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(id="input1", name="Input 1", type="any", required=True),
                InputPort(
                    id="input2",
                    name="Input 2",
                    type="any",
                    required=True,
                    default="default2",
                ),
            ],
            outputs=[],
        )

        state.available_inputs["test_node.input1"] = "value1"

        inputs = executor.collect_inputs(node)
        assert inputs == {"input1": "value1", "input2": "default2"}


class TestExecuteNode:
    def test_execute_start_node(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = StartNode(
            id="start",
            name="Start",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            outputs=[
                OutputPort(
                    id="output",
                    name="Output",
                    type="any",
                    required=True,
                    default="test_value"
                ),
            ],
        )

        outputs = executor.execute_node(node)

        record = state.history.get_record("start")
        assert record.status == NodeStatus.COMPLETED
        assert outputs == {"output": "test_value"}

    def test_execute_pass_node(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="pass",
            name="Pass",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(id="input", name="Input", type="any", required=True),
            ],
            outputs=[
                OutputPort(id="input", name="Output", type="any", required=True),
            ],
        )

        state.available_inputs["pass.input"] = "test_value"
        outputs = executor.execute_node(node)

        record = state.history.get_record("pass")
        assert record.status == NodeStatus.COMPLETED
        assert outputs == {"input": "test_value"}

    def test_execute_end_node(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = EndNode(
            id="end",
            name="End",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(id="input", name="Input", type="any", required=True),
            ],
        )

        state.available_inputs["end.input"] = "test_value"
        outputs = executor.execute_node(node)

        record = state.history.get_record("end")
        assert record.status == NodeStatus.COMPLETED
        assert outputs == {"input": "test_value"}

    def test_execute_action_node_with_custom_handler(self):
        state = ExecutionState()
        registry = ActionRegistry()

        def custom_handler(ctx, params):
            return {"result": params.get("value", 0) * 2}

        registry.register("double", custom_handler)
        executor = NodeExecutor(state, action_registry=registry)

        node = ActionNode(
            id="action",
            name="Double Action",
            action_type="double",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            metadata={},
            inputs=[
                InputPort(id="value", name="Value", type="number", required=True),
            ],
            outputs=[
                OutputPort(id="result", name="Result", type="number", required=True),
            ],
        )

        state.available_inputs["action.value"] = 5
        outputs = executor.execute_node(node)

        record = state.history.get_record("action")
        assert record.status == NodeStatus.COMPLETED
        assert outputs == {"result": 10}


class TestRetryLogic:
    def test_retry_on_failure(self):
        state = ExecutionState()
        registry = ActionRegistry()

        attempt_count = 0

        def flaky_handler(ctx, params):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return {"result": "success"}

        registry.register("flaky", flaky_handler)
        executor = NodeExecutor(state, action_registry=registry)

        node = ActionNode(
            id="action",
            name="Flaky Action",
            action_type="flaky",
            retry=RetrySpec(attempts=3, backoff_seconds=0),
            metadata={},
            inputs=[],
            outputs=[
                OutputPort(id="result", name="Result", type="any", required=True),
            ],
        )

        outputs = executor.execute_node(node)

        record = state.history.get_record("action")
        assert record.status == NodeStatus.COMPLETED
        assert record.retry_count == 2
        assert attempt_count == 3
        assert outputs == {"result": "success"}

    def test_retry_exhausted(self):
        state = ExecutionState()
        registry = ActionRegistry()

        attempt_count = 0

        def always_fails(ctx, params):
            nonlocal attempt_count
            attempt_count += 1
            raise Exception("Always fails")

        registry.register("fails", always_fails)
        executor = NodeExecutor(state, action_registry=registry)

        node = ActionNode(
            id="action",
            name="Failing Action",
            action_type="fails",
            retry=RetrySpec(attempts=2, backoff_seconds=0),
            metadata={},
            inputs=[],
            outputs=[
                OutputPort(id="result", name="Result", type="any", required=True),
            ],
        )

        with pytest.raises(Exception, match="Always fails"):
            executor.execute_node(node)

        record = state.history.get_record("action")
        assert record.status == NodeStatus.FAILED
        assert record.retry_count == 2
        assert attempt_count == 3

    def test_retry_backoff(self):
        with patch("time.sleep") as mock_sleep:
            state = ExecutionState()
            registry = ActionRegistry()

            attempt_count = 0

            def flaky_handler(ctx, params):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise Exception("Temporary failure")
                return {"result": "success"}

            registry.register("flaky", flaky_handler)
            executor = NodeExecutor(state, action_registry=registry)

            node = ActionNode(
                id="action",
                name="Flaky Action",
                action_type="flaky",
                retry=RetrySpec(attempts=2, backoff_seconds=1.5),
                metadata={},
                inputs=[],
                outputs=[
                    OutputPort(id="result", name="Result", type="any", required=True),
                ],
            )

            executor.execute_node(node)

            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(1.5)


class TestErrorHandling:
    def test_unknown_action_type(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = ActionNode(
            id="action",
            name="Unknown Action",
            action_type="nonexistent",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            metadata={},
            inputs=[],
            outputs=[],
        )

        with pytest.raises(Exception, match="Action type 'nonexistent' not found"):
            executor.execute_node(node)

        record = state.history.get_record("action")
        assert record.status == NodeStatus.FAILED

    def test_missing_action_type(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = ActionNode(
            id="action",
            name="No Action Type",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            metadata={},
            inputs=[],
            outputs=[],
        )

        with pytest.raises(Exception, match="Action type not specified"):
            executor.execute_node(node)

        record = state.history.get_record("action")
        assert record.status == NodeStatus.FAILED

    def test_unknown_node_type(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = StartNode(
            id="unknown",
            name="Unknown",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            outputs=[],
        )
        node.type = "unknown"

        with pytest.raises(ValueError, match="Unknown node type: unknown"):
            executor._execute_node_logic(node, {})


class TestMarkNodeSkipped:
    def test_mark_node_skipped(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="node",
            name="Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[],
        )

        executor.mark_node_skipped(node)

        record = state.history.get_record("node")
        assert record.status == NodeStatus.SKIPPED


class TestLifecycleHooks:
    def test_before_execute(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="node",
            name="Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[],
        )

        executor.before_execute(node)

        assert len(state.history.logs) == 1
        assert "Starting execution of node: node" in state.history.logs[0]

    def test_after_execute(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="node",
            name="Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[],
        )

        executor.after_execute(node, {"result": "success"})

        assert len(state.history.logs) == 1
        assert "Completed execution of node: node" in state.history.logs[0]

    def test_on_error(self):
        state = ExecutionState()
        executor = NodeExecutor(state)

        node = PassNode(
            id="node",
            name="Node",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[],
            outputs=[],
        )

        executor.on_error(node, "Something went wrong")

        assert len(state.history.logs) == 1
        assert "Error in node node: Something went wrong" in state.history.logs[0]
