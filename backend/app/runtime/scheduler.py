# @file /backend/app/runtime/scheduler.py
# @brief DAG工作流引擎 - 调度器（拓扑排序、入度管理、就绪队列）
# @create 2026-04-01 00:00:00

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Set

from app.runtime.dag_models import BaseNode, DAGWorkflow, Edge
from app.runtime.execution_state import ExecutionState, NodeStatus


class DAGScheduler:
    def __init__(self, workflow: DAGWorkflow, state: ExecutionState) -> None:
        self.workflow = workflow
        self.state = state
        self.in_degree: Dict[str, int] = {}
        self.adjacency: Dict[str, List[str]] = {}
        self.port_dependencies: Dict[str, Set[str]] = {}
        self.ready_queue: deque[str] = deque()

        self._initialize()

    def _initialize(self) -> None:
        self._build_graph()
        self._calculate_in_degree()
        self._find_ready_nodes()

    def _build_graph(self) -> None:
        node_ids = list(self.workflow.nodes.keys())
        self.adjacency = {node_id: [] for node_id in node_ids}
        self.in_degree = {node_id: 0 for node_id in node_ids}
        self.port_dependencies = {node_id: set() for node_id in node_ids}

        for edge in self.workflow.edges:
            source_node_id = edge.source.split(".")[0]
            target_node_id = edge.target.split(".")[0]
            target_port_id = edge.target.split(".")[1]

            self.adjacency[source_node_id].append(target_node_id)
            self.port_dependencies[target_node_id].add(target_port_id)

    def _calculate_in_degree(self) -> None:
        for node_id, node in self.workflow.nodes.items():
            required_ports = [p.id for p in node.inputs if p.required]
            self.in_degree[node_id] = len(required_ports)

    def _find_ready_nodes(self) -> None:
        for node_id, degree in self.in_degree.items():
            if degree == 0:
                record = self.state.history.get_record(node_id)
                if record.status == NodeStatus.PENDING:
                    self.ready_queue.append(node_id)

    def topological_sort(self) -> List[str]:
        return self.workflow.topological_sort()

    def has_cycle(self) -> bool:
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True

    def get_ready_node(self) -> str | None:
        if self.ready_queue:
            return self.ready_queue.popleft()
        return None

    def mark_node_completed(self, node_id: str) -> None:
        record = self.state.history.get_record(node_id)
        if record.status != NodeStatus.COMPLETED:
            return

        for neighbor in self.adjacency.get(node_id, []):
            self._update_neighbor_in_degree(neighbor, node_id)

    def _update_neighbor_in_degree(
        self, neighbor_id: str, completed_node_id: str
    ) -> None:
        for edge in self.workflow.edges:
            if edge.source.startswith(f"{completed_node_id}."):
                target_node_id, target_port_id = edge.target.split(".")
                if target_node_id == neighbor_id:
                    port_key = f"{target_node_id}.{target_port_id}"
                    if port_key in self.state.available_inputs:
                        self.in_degree[neighbor_id] -= 1

        if self.in_degree[neighbor_id] <= 0:
            record = self.state.history.get_record(neighbor_id)
            if record.status == NodeStatus.PENDING:
                self.ready_queue.append(neighbor_id)

    def is_all_nodes_processed(self) -> bool:
        for node_id in self.workflow.nodes:
            record = self.state.history.get_record(node_id)
            if record.status in [NodeStatus.PENDING, NodeStatus.RUNNING]:
                return False
        return True

    def has_ready_nodes(self) -> bool:
        return len(self.ready_queue) > 0

    def reset(self) -> None:
        self.ready_queue.clear()
        self._initialize()
