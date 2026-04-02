# @file /backend/app/runtime/dag_models.py
# @brief DAG工作流引擎核心数据模型定义
# @create 2026-04-01 00:00:00

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

PortDataType = Literal["any", "string", "number", "boolean", "object", "array"]


class _Base(BaseModel):
    model_config = {"extra": "forbid"}


class Port(_Base):
    id: str
    name: str
    type: PortDataType = "any"
    required: bool = True
    default: Any = None


class InputPort(Port):
    pass


class OutputPort(Port):
    condition: Optional[str] = None
    case: Optional[Any] = None
    index: Optional[int] = None
    field: Optional[str] = None


class RetrySpec(_Base):
    attempts: int = 0
    backoff_seconds: float = 0.0


class InputMapping(_Base):
    external_port_id: str
    internal_node_id: str
    internal_port_id: str


class OutputMapping(_Base):
    external_port_id: str
    internal_node_id: str
    internal_port_id: str


class InternalSubgraph(_Base):
    nodes: Dict[str, BaseNode] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)


class GroupConfig(_Base):
    internal_subgraph: InternalSubgraph = Field(default_factory=InternalSubgraph)
    input_mappings: List[InputMapping] = Field(default_factory=list)
    output_mappings: List[OutputMapping] = Field(default_factory=list)


class SubflowConfig(_Base):
    subflow_id: str
    subflow_version: Optional[str] = None
    input_mappings: List[InputMapping] = Field(default_factory=list)
    output_mappings: List[OutputMapping] = Field(default_factory=list)


class BaseNode(_Base):
    id: str
    name: str
    type: str
    retry: RetrySpec = Field(default_factory=RetrySpec)
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    inputs: List[InputPort] = Field(default_factory=list)
    outputs: List[OutputPort] = Field(default_factory=list)
    error_port: OutputPort = Field(
        default_factory=lambda: OutputPort(
            id="error", name="Error", type="any", required=False
        )
    )


class Edge(_Base):
    id: str
    source: str
    target: str


class MessageMetadata(_Base):
    timestamp: str
    source_node: str
    source_port: str


class Message(_Base):
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: MessageMetadata


class DAGWorkflow(_Base):
    version: str = "2.0"
    name: str
    description: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    nodes: Dict[str, BaseNode] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)

    def validate(self) -> bool:
        self._check_cycles()
        self._check_ports()
        self._check_start_end_nodes()
        return True

    def _check_cycles(self) -> None:
        visited = set()
        path = set()

        def dfs(node_id: str) -> bool:
            if node_id in path:
                raise ValueError(f"Cycle detected involving node: {node_id}")
            if node_id in visited:
                return False

            visited.add(node_id)
            path.add(node_id)

            for edge in self.edges:
                if edge.source.startswith(f"{node_id}."):
                    target_node_id = edge.target.split(".")[0]
                    if dfs(target_node_id):
                        return True

            path.remove(node_id)
            return False

        for node_id in self.nodes:
            if dfs(node_id):
                raise ValueError("Cycle detected in DAG")

    def _check_ports(self) -> None:
        for edge in self.edges:
            source_node_id, source_port_id = edge.source.split(".")
            target_node_id, target_port_id = edge.target.split(".")

            if source_node_id not in self.nodes:
                raise ValueError(f"Source node {source_node_id} not found")
            if target_node_id not in self.nodes:
                raise ValueError(f"Target node {target_node_id} not found")

            source_node = self.nodes[source_node_id]
            target_node = self.nodes[target_node_id]

            source_ports = source_node.outputs + [source_node.error_port]
            if not any(p.id == source_port_id for p in source_ports):
                raise ValueError(
                    f"Source port {source_port_id} not found on node {source_node_id}"
                )

            if not any(p.id == target_port_id for p in target_node.inputs):
                raise ValueError(
                    f"Target port {target_port_id} not found on node {target_node_id}"
                )

    def _check_start_end_nodes(self) -> None:
        has_start = any(node.type == "start" for node in self.nodes.values())
        has_end = any(node.type == "end" for node in self.nodes.values())

        if not has_start:
            raise ValueError("DAG must contain a Start node")
        if not has_end:
            raise ValueError("DAG must contain an End node")

    def topological_sort(self) -> List[str]:
        in_degree = {node_id: 0 for node_id in self.nodes}
        adjacency = {node_id: [] for node_id in self.nodes}

        for edge in self.edges:
            source_node_id = edge.source.split(".")[0]
            target_node_id = edge.target.split(".")[0]

            adjacency[source_node_id].append(target_node_id)
            in_degree[target_node_id] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in DAG")

        return result

    def get_ready_nodes(self, available_inputs: Dict[str, Dict[str, Any]]) -> List[str]:
        ready_nodes = []

        for node_id, node in self.nodes.items():
            required_inputs = [p for p in node.inputs if p.required]
            all_required_available = True

            for port in required_inputs:
                port_key = f"{node_id}.{port.id}"
                if port_key not in available_inputs:
                    all_required_available = False
                    break

            if all_required_available:
                ready_nodes.append(node_id)

        return ready_nodes
