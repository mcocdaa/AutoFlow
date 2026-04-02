# @file /backend/tests/test_dag_scheduler.py
# @brief 测试 DAG 调度器、拓扑排序、循环检测、入度管理
# @create 2026-04-01

from __future__ import annotations

import pytest

from app.runtime.dag_models import (
    BaseNode,
    DAGWorkflow,
    Edge,
    InputPort,
    OutputPort,
    RetrySpec,
)
from app.runtime.execution_state import ExecutionState, NodeStatus
from app.runtime.nodes import EndNode, PassNode, StartNode
from app.runtime.scheduler import DAGScheduler


def create_simple_dag():
    """创建简单的线性 DAG 用于测试"""
    start_node = StartNode(
        id="start",
        name="Start",
        type="start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass_node = PassNode(
        id="pass",
        name="Pass",
        type="pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        type="end",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[],
    )
    workflow = DAGWorkflow(
        name="Simple DAG",
        nodes={
            "start": start_node,
            "pass": pass_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.output", target="pass.input"),
            Edge(id="e2", source="pass.output", target="end.input"),
        ],
    )
    return workflow


def create_dag_with_branch():
    """创建带分支的 DAG 用于测试"""
    start_node = StartNode(
        id="start",
        name="Start",
        type="start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass1_node = PassNode(
        id="pass1",
        name="Pass 1",
        type="pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass2_node = PassNode(
        id="pass2",
        name="Pass 2",
        type="pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        type="end",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[
            InputPort(id="input1", name="Input 1", type="any", required=True),
            InputPort(id="input2", name="Input 2", type="any", required=True),
        ],
        outputs=[],
    )
    workflow = DAGWorkflow(
        name="Branched DAG",
        nodes={
            "start": start_node,
            "pass1": pass1_node,
            "pass2": pass2_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.output", target="pass1.input"),
            Edge(id="e2", source="start.output", target="pass2.input"),
            Edge(id="e3", source="pass1.output", target="end.input1"),
            Edge(id="e4", source="pass2.output", target="end.input2"),
        ],
    )
    return workflow


def create_dag_with_cycle():
    """创建带循环的 DAG 用于测试"""
    start_node = StartNode(
        id="start",
        name="Start",
        type="start",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass1_node = PassNode(
        id="pass1",
        name="Pass 1",
        type="pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    pass2_node = PassNode(
        id="pass2",
        name="Pass 2",
        type="pass",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any", required=True)],
    )
    end_node = EndNode(
        id="end",
        name="End",
        type="end",
        retry=RetrySpec(attempts=0, backoff_seconds=0),
        config={},
        metadata={},
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[],
    )
    workflow = DAGWorkflow(
        name="Cyclic DAG",
        nodes={
            "start": start_node,
            "pass1": pass1_node,
            "pass2": pass2_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.output", target="pass1.input"),
            Edge(id="e2", source="pass1.output", target="pass2.input"),
            Edge(id="e3", source="pass2.output", target="pass1.input"),  # 循环
            Edge(id="e4", source="pass2.output", target="end.input"),
        ],
    )
    return workflow


class TestDAGSchedulerCreation:
    def test_scheduler_creation(self):
        """测试 DAGScheduler 创建"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert scheduler.workflow is workflow
        assert scheduler.state is state
        assert isinstance(scheduler.adjacency, dict)
        assert isinstance(scheduler.in_degree, dict)

    def test_initial_graph_building(self):
        """测试初始图构建"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert "start" in scheduler.adjacency
        assert "pass" in scheduler.adjacency
        assert "end" in scheduler.adjacency
        assert "pass" in scheduler.adjacency["start"]
        assert "end" in scheduler.adjacency["pass"]


class TestTopologicalSort:
    def test_topological_sort_simple_dag(self):
        """测试简单 DAG 的拓扑排序"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        order = scheduler.topological_sort()
        assert len(order) == 3
        assert order.index("start") < order.index("pass")
        assert order.index("pass") < order.index("end")

    def test_topological_sort_branched_dag(self):
        """测试带分支 DAG 的拓扑排序"""
        workflow = create_dag_with_branch()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        order = scheduler.topological_sort()
        assert len(order) == 4
        assert order.index("start") < order.index("pass1")
        assert order.index("start") < order.index("pass2")
        assert order.index("pass1") < order.index("end")
        assert order.index("pass2") < order.index("end")

    def test_topological_sort_cyclic_dag_raises_error(self):
        """测试带循环 DAG 的拓扑排序抛出错误"""
        workflow = create_dag_with_cycle()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        with pytest.raises(ValueError, match="Cycle detected"):
            scheduler.topological_sort()


class TestCycleDetection:
    def test_has_cycle_false_for_acyclic(self):
        """测试无循环的 DAG 返回 False"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert not scheduler.has_cycle()

    def test_has_cycle_true_for_cyclic(self):
        """测试带循环的 DAG 返回 True"""
        workflow = create_dag_with_cycle()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert scheduler.has_cycle()


class TestInDegreeManagement:
    def test_initial_in_degree_calculation(self):
        """测试初始入度计算"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert scheduler.in_degree["start"] == 0
        assert scheduler.in_degree["pass"] == 1
        assert scheduler.in_degree["end"] == 1

    def test_initial_in_degree_branched(self):
        """测试带分支 DAG 的初始入度计算"""
        workflow = create_dag_with_branch()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert scheduler.in_degree["start"] == 0
        assert scheduler.in_degree["pass1"] == 1
        assert scheduler.in_degree["pass2"] == 1
        assert scheduler.in_degree["end"] == 2


class TestReadyQueue:
    def test_get_ready_node_initial(self):
        """测试初始就绪节点获取"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        ready_node = scheduler.get_ready_node()
        assert ready_node == "start"
        assert scheduler.get_ready_node() is None

    def test_has_ready_nodes_initial(self):
        """测试初始是否有待处理就绪节点"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert scheduler.has_ready_nodes()

    def test_has_ready_nodes_after_all_processed(self):
        """测试所有节点处理完毕后无就绪节点"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        scheduler.get_ready_node()  # 取走 start
        assert not scheduler.has_ready_nodes()


class TestMarkNodeCompleted:
    def test_mark_node_completed_propagates(self):
        """测试标记节点完成后传播到后续节点"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)

        # 先获取 start 节点并标记为完成
        scheduler.get_ready_node()
        record = state.history.get_record("start")
        record.status = NodeStatus.COMPLETED
        state.available_inputs["pass.input"] = "some data"

        scheduler.mark_node_completed("start")

        # pass 节点应该就绪
        assert scheduler.has_ready_nodes()
        ready_node = scheduler.get_ready_node()
        assert ready_node == "pass"


class TestAllNodesProcessed:
    def test_is_all_nodes_processed_initial(self):
        """测试初始状态所有节点未处理完"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)
        assert not scheduler.is_all_nodes_processed()

    def test_is_all_nodes_processed_true(self):
        """测试所有节点处理完"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)

        for node_id in workflow.nodes:
            record = state.history.get_record(node_id)
            record.status = NodeStatus.COMPLETED

        assert scheduler.is_all_nodes_processed()


class TestSchedulerReset:
    def test_reset_scheduler(self):
        """测试重置调度器"""
        workflow = create_simple_dag()
        state = ExecutionState()
        scheduler = DAGScheduler(workflow, state)

        # 处理掉 start 节点
        scheduler.get_ready_node()
        assert not scheduler.has_ready_nodes()

        # 重置
        scheduler.reset()

        # 应该再次有就绪节点
        assert scheduler.has_ready_nodes()
        ready_node = scheduler.get_ready_node()
        assert ready_node == "start"
