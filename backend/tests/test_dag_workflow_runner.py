# @file /backend/tests/test_dag_workflow_runner.py
# @brief 测试 DAG 工作流运行器、整合调度器和执行器、完整工作流执行
# @create 2026-04-01

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.actions import ActionRegistry
from app.runtime.dag_models import (
    DAGWorkflow,
    Edge,
    InputPort,
    OutputPort,
    RetrySpec,
)
from app.runtime.execution_state import NodeStatus, WorkflowStatus
from app.runtime.nodes import ActionNode, EndNode, PassNode, StartNode
from app.runtime.workflow_runner import WorkflowRunner


def create_simple_workflow():
    """创建简单工作流用于测试"""
    start_node = StartNode(
        id="start",
        name="Start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        outputs=[
            OutputPort(
                id="input_value",
                name="Input Value",
                type="number",
                required=True,
                default=0,
            ),
        ],
    )
    pass_node = PassNode(
        id="pass",
        name="Pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="value", name="Value", type="number", required=True)],
        outputs=[OutputPort(id="value", name="Value", type="number", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="result", name="Result", type="number", required=True)],
    )
    workflow = DAGWorkflow(
        name="Simple Workflow",
        nodes={
            "start": start_node,
            "pass": pass_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.input_value", target="pass.value"),
            Edge(id="e2", source="pass.value", target="end.result"),
        ],
    )
    return workflow


def create_workflow_with_action():
    """创建带 Action 的工作流"""
    registry = ActionRegistry()

    def double_handler(ctx, params):
        return {"result": params.get("value", 0) * 2}

    registry.register("double", double_handler)

    start_node = StartNode(
        id="start",
        name="Start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        outputs=[
            OutputPort(
                id="input_value", name="Input Value", type="number", required=True
            ),
        ],
    )
    action_node = ActionNode(
        id="double",
        name="Double",
        action_type="double",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        metadata={},
        inputs=[InputPort(id="value", name="Value", type="number", required=True)],
        outputs=[OutputPort(id="result", name="Result", type="number", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="result", name="Result", type="number", required=True)],
    )
    workflow = DAGWorkflow(
        name="Action Workflow",
        nodes={
            "start": start_node,
            "double": action_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.input_value", target="double.value"),
            Edge(id="e2", source="double.result", target="end.result"),
        ],
    )
    return workflow, registry


def create_branched_workflow():
    """创建带分支的工作流"""
    start_node = StartNode(
        id="start",
        name="Start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        outputs=[
            OutputPort(id="value", name="Value", type="number", required=True),
        ],
    )
    pass1_node = PassNode(
        id="pass1",
        name="Pass 1",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="value", name="Value", type="number", required=True)],
        outputs=[OutputPort(id="value", name="Value", type="number", required=True)],
    )
    pass2_node = PassNode(
        id="pass2",
        name="Pass 2",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="value", name="Value", type="number", required=True)],
        outputs=[OutputPort(id="value", name="Value", type="number", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[
            InputPort(id="value1", name="Value 1", type="number", required=True),
            InputPort(id="value2", name="Value 2", type="number", required=True),
        ],
    )
    workflow = DAGWorkflow(
        name="Branched Workflow",
        nodes={
            "start": start_node,
            "pass1": pass1_node,
            "pass2": pass2_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.value", target="pass1.value"),
            Edge(id="e2", source="start.value", target="pass2.value"),
            Edge(id="e3", source="pass1.value", target="end.value1"),
            Edge(id="e4", source="pass2.value", target="end.value2"),
        ],
    )
    return workflow


class TestWorkflowRunnerCreation:
    def test_runner_creation(self):
        """测试 WorkflowRunner 创建"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)
        assert runner.workflow is workflow
        assert runner.state is not None
        assert runner.scheduler is not None
        assert runner.executor is not None
        assert runner.data_router is not None

    def test_runner_with_custom_registry(self):
        """测试 WorkflowRunner 带自定义 ActionRegistry"""
        workflow, registry = create_workflow_with_action()
        runner = WorkflowRunner(workflow, action_registry=registry)
        assert runner.action_registry is registry


class TestSimpleWorkflowExecution:
    def test_run_simple_workflow(self):
        """测试运行简单工作流"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        result = runner.run({"input_value": 42})

        assert result == {"result": 42}
        assert runner.state.workflow_status == WorkflowStatus.COMPLETED

    def test_run_simple_workflow_with_default(self):
        """测试使用默认值运行简单工作流"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        result = runner.run({})

        assert result == {"result": 0}
        assert runner.state.workflow_status == WorkflowStatus.COMPLETED


class TestWorkflowWithAction:
    def test_run_workflow_with_action(self):
        """测试运行带 Action 的工作流"""
        workflow, registry = create_workflow_with_action()
        runner = WorkflowRunner(workflow, action_registry=registry)

        result = runner.run({"input_value": 5})

        assert result == {"result": 10}
        assert runner.state.workflow_status == WorkflowStatus.COMPLETED


class TestBranchedWorkflow:
    def test_run_branched_workflow(self):
        """测试运行带分支的工作流"""
        workflow = create_branched_workflow()
        runner = WorkflowRunner(workflow)

        result = runner.run({"value": 10})

        assert result == {"value1": 10, "value2": 10}
        assert runner.state.workflow_status == WorkflowStatus.COMPLETED


class TestWorkflowExecutionHistory:
    def test_get_execution_history(self):
        """测试获取执行历史"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        runner.run({"input_value": 42})
        history = runner.get_execution_history()

        assert "status" in history
        assert history["status"] == WorkflowStatus.COMPLETED
        assert "records" in history
        assert "start" in history["records"]
        assert "pass" in history["records"]
        assert "end" in history["records"]
        assert "logs" in history

    def test_execution_history_node_statuses(self):
        """测试执行历史中的节点状态"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        runner.run({"input_value": 42})
        history = runner.get_execution_history()

        assert history["records"]["start"]["status"] == NodeStatus.COMPLETED
        assert history["records"]["pass"]["status"] == NodeStatus.COMPLETED
        assert history["records"]["end"]["status"] == NodeStatus.COMPLETED


class TestWorkflowInitialization:
    def test_initialize_workflow_with_inputs(self):
        """测试使用输入初始化工作流"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        runner._initialize_workflow({"input_value": 100})

        assert "start.input_value" in runner.state.available_inputs
        assert runner.state.available_inputs["start.input_value"] == 100

    def test_initialize_workflow_with_defaults(self):
        """测试使用默认值初始化工作流"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        runner._initialize_workflow({})

        assert "start.input_value" in runner.state.available_inputs
        assert runner.state.available_inputs["start.input_value"] == 0


class TestWorkflowFinalization:
    def test_finalize_workflow_completed(self):
        """测试工作流完成后的最终化"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        # 标记所有节点为完成
        for node_id in workflow.nodes:
            record = runner.state.history.get_record(node_id)
            record.status = NodeStatus.COMPLETED

        runner._finalize_workflow()

        assert runner.state.workflow_status == WorkflowStatus.COMPLETED

    def test_finalize_workflow_failed(self):
        """测试工作流失败后的最终化"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        # 标记一个节点为失败
        record = runner.state.history.get_record("pass")
        record.status = NodeStatus.FAILED

        runner._finalize_workflow()

        assert runner.state.workflow_status == WorkflowStatus.FAILED

    def test_finalize_workflow_stopped(self):
        """测试工作流停止后的最终化"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        # 标记一些节点为完成，一些为待处理
        record_start = runner.state.history.get_record("start")
        record_start.status = NodeStatus.COMPLETED
        record_pass = runner.state.history.get_record("pass")
        record_pass.status = NodeStatus.PENDING

        runner._finalize_workflow()

        assert runner.state.workflow_status == WorkflowStatus.STOPPED


class TestWorkflowOutput:
    def test_get_workflow_output(self):
        """测试获取工作流输出"""
        workflow = create_simple_workflow()
        runner = WorkflowRunner(workflow)

        # 设置 end 节点的输出
        record = runner.state.history.get_record("end")
        record.outputs = {"result": 123}

        output = runner._get_workflow_output()

        assert output == {"result": 123}


class TestWorkflowWithError:
    def test_run_workflow_with_error_raises_exception(self):
        """测试运行出错的工作流会抛出异常"""
        # 创建一个会导致错误的工作流
        workflow = DAGWorkflow(
            name="Error Workflow",
            nodes={},
            edges=[],
        )

        start_node = StartNode(
            id="start",
            name="Start",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            outputs=[
                OutputPort(id="value", name="Value", type="number", required=True),
            ],
        )
        workflow.nodes["start"] = start_node

        action_node = ActionNode(
            id="error_action",
            name="Error Action",
            action_type="nonexistent",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            metadata={},
            inputs=[InputPort(id="value", name="Value", type="number", required=True)],
            outputs=[
                OutputPort(id="result", name="Result", type="number", required=True)
            ],
        )
        workflow.nodes["error_action"] = action_node

        end_node = EndNode(
            id="end",
            name="End",
            retry=RetrySpec(attempts=0, backoff_seconds=0),
            config={},
            metadata={},
            inputs=[
                InputPort(id="result", name="Result", type="number", required=True)
            ],
        )
        workflow.nodes["end"] = end_node

        workflow.edges = [
            Edge(id="e1", source="start.value", target="error_action.value"),
            Edge(id="e2", source="error_action.result", target="end.result"),
        ]

        runner = WorkflowRunner(workflow)

        with pytest.raises(Exception):
            runner.run({"value": 10})

        assert runner.state.workflow_status == WorkflowStatus.FAILED
