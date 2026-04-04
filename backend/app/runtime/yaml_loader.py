from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

from app.runtime.dag_models import (
    BaseNode,
    DAGWorkflow,
    Edge,
    GroupConfig,
    InputMapping,
    InputPort,
    InternalSubgraph,
    OutputMapping,
    OutputPort,
    RetrySpec,
    SubflowConfig,
)
from app.runtime.nodes import (
    ActionNode,
    EndNode,
    ForNode,
    GroupNode,
    IfNode,
    InputNode,
    MergeNode,
    PassNode,
    RetryNode,
    SplitNode,
    StartNode,
    SubflowNode,
    SwitchNode,
    WhileNode,
)


class YAMLLoaderError(Exception):
    pass


class YAMLLoader:
    SUPPORTED_VERSION = "2.0"

    NODE_TYPE_MAP = {
        "start": StartNode,
        "end": EndNode,
        "action": ActionNode,
        "pass": PassNode,
        "merge": MergeNode,
        "split": SplitNode,
        "if": IfNode,
        "switch": SwitchNode,
        "for": ForNode,
        "while": WhileNode,
        "retry": RetryNode,
        "group": GroupNode,
        "subflow": SubflowNode,
        "input": InputNode,
    }

    @classmethod
    def load(cls, yaml_str: str) -> DAGWorkflow:
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise YAMLLoaderError(f"YAML parse error: {e}") from e

        cls._validate_top_level(data)
        cls._validate_version(data)

        return cls._build_workflow(data)

    @classmethod
    def _validate_top_level(cls, data: Dict[str, Any]) -> None:
        required_fields = ["version", "name"]
        for field in required_fields:
            if field not in data:
                raise YAMLLoaderError(f"Missing required field: {field}")

        if "nodes" not in data:
            raise YAMLLoaderError("Missing required field: nodes")

        if "edges" not in data:
            raise YAMLLoaderError("Missing required field: edges")

    @classmethod
    def _validate_version(cls, data: Dict[str, Any]) -> None:
        version = data.get("version")
        if version != cls.SUPPORTED_VERSION:
            raise YAMLLoaderError(
                f"Unsupported version: {version}, expected: {cls.SUPPORTED_VERSION}"
            )

    @classmethod
    def _build_workflow(cls, data: Dict[str, Any]) -> DAGWorkflow:
        nodes = cls._build_nodes(data.get("nodes", {}))
        edges = cls._build_edges(data.get("edges", []), nodes)

        workflow = DAGWorkflow(
            name=data["name"],
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            inputs=data.get("inputs", {}),
        )

        cls._validate_workflow(workflow)
        return workflow

    @classmethod
    def _build_nodes(cls, nodes_data: Dict[str, Any]) -> Dict[str, BaseNode]:
        nodes: Dict[str, BaseNode] = {}
        for node_id, node_data in nodes_data.items():
            node = cls._build_node(node_id, node_data)
            nodes[node_id] = node
        return nodes

    @classmethod
    def _build_node(cls, node_id: str, node_data: Dict[str, Any]) -> BaseNode:
        node_type = node_data.get("type")
        if node_type not in cls.NODE_TYPE_MAP:
            raise YAMLLoaderError(f"Unknown node type: {node_type}")

        node_class = cls.NODE_TYPE_MAP[node_type]

        retry_data = node_data.get("retry", {})
        retry = RetrySpec(
            attempts=retry_data.get("attempts", 0),
            backoff_seconds=retry_data.get("backoff_seconds", 0.0),
        )

        inputs = cls._build_input_ports(node_data.get("inputs", []))
        outputs = cls._build_output_ports(node_data.get("outputs", []))

        kwargs: Dict[str, Any] = {
            "id": node_id,
            "name": node_data.get("name", node_id),
            "retry": retry,
            "config": node_data.get("config", {}),
            "metadata": node_data.get("metadata", {}),
        }

        if node_type not in ["start", "end"]:
            kwargs["inputs"] = inputs
            kwargs["outputs"] = outputs
        elif node_type == "start":
            kwargs["outputs"] = outputs
        elif node_type == "end":
            kwargs["inputs"] = inputs

        if node_type in ["group", "subflow"]:
            kwargs = cls._add_composite_node_kwargs(kwargs, node_data, node_type)

        return node_class(**kwargs)

    @classmethod
    def _add_composite_node_kwargs(
        cls, kwargs: Dict[str, Any], node_data: Dict[str, Any], node_type: str
    ) -> Dict[str, Any]:
        inner_nodes = cls._build_nodes(node_data.get("inner_nodes", {}))
        inner_edges = cls._build_edges(node_data.get("inner_edges", []), inner_nodes)
        internal_subgraph = InternalSubgraph(
            nodes=inner_nodes,
            edges=inner_edges,
        )

        port_mapping = node_data.get("port_mapping", {})
        input_mappings = [InputMapping(**m) for m in port_mapping.get("inputs", [])]
        output_mappings = [OutputMapping(**m) for m in port_mapping.get("outputs", [])]

        config = kwargs.get("config", {})
        if node_type == "group":
            config["group_config"] = GroupConfig(
                internal_subgraph=internal_subgraph,
                input_mappings=input_mappings,
                output_mappings=output_mappings,
            ).model_dump()
        else:
            config["subflow_config"] = SubflowConfig(
                subflow_id=node_data.get("subflow_id", ""),
                subflow_version=node_data.get("subflow_version"),
                input_mappings=input_mappings,
                output_mappings=output_mappings,
            ).model_dump()

        kwargs["config"] = config
        return kwargs

    @classmethod
    def _build_input_ports(cls, ports_data: List[Dict[str, Any]]) -> List[InputPort]:
        return [InputPort(**port_data) for port_data in ports_data]

    @classmethod
    def _build_output_ports(cls, ports_data: List[Dict[str, Any]]) -> List[OutputPort]:
        return [OutputPort(**port_data) for port_data in ports_data]

    @classmethod
    def _build_edges(
        cls, edges_data: List[Dict[str, Any]], nodes: Dict[str, BaseNode]
    ) -> List[Edge]:
        edges = []
        for edge_data in edges_data:
            source = edge_data.get("source")
            target = edge_data.get("target")
            if not source or not target:
                raise YAMLLoaderError("Edge missing source or target")

            source_node_id, source_port_id = cls._parse_port_ref(source)
            target_node_id, target_port_id = cls._parse_port_ref(target)

            if source_node_id not in nodes:
                raise YAMLLoaderError(f"Source node not found: {source_node_id}")
            if target_node_id not in nodes:
                raise YAMLLoaderError(f"Target node not found: {target_node_id}")

            edges.append(
                Edge(
                    id=edge_data.get("id", f"{source}-{target}"),
                    source=source,
                    target=target,
                )
            )
        return edges

    @classmethod
    def _parse_port_ref(cls, ref: str) -> tuple[str, str]:
        parts = ref.split(".", 1)
        if len(parts) != 2:
            raise YAMLLoaderError(f"Invalid port reference: {ref}")
        return parts[0], parts[1]

    @classmethod
    def _validate_workflow(cls, workflow: DAGWorkflow) -> None:
        cls._validate_start_end_nodes(workflow)
        cls._validate_no_cycles(workflow)
        cls._validate_port_connections(workflow)

    @classmethod
    def _validate_start_end_nodes(cls, workflow: DAGWorkflow) -> None:
        has_start = any(node.type == "start" for node in workflow.nodes.values())
        has_end = any(node.type == "end" for node in workflow.nodes.values())
        if not has_start:
            raise YAMLLoaderError("Workflow must have a Start node")
        if not has_end:
            raise YAMLLoaderError("Workflow must have an End node")

    @classmethod
    def _validate_no_cycles(cls, workflow: DAGWorkflow) -> None:
        visited: set[str] = set()
        recursion_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            if node_id in recursion_stack:
                return True
            if node_id in visited:
                return False

            visited.add(node_id)
            recursion_stack.add(node_id)

            for edge in workflow.edges:
                source_node_id, _ = cls._parse_port_ref(edge.source)
                if source_node_id == node_id:
                    target_node_id, _ = cls._parse_port_ref(edge.target)
                    if dfs(target_node_id):
                        return True

            recursion_stack.remove(node_id)
            return False

        for node_id in workflow.nodes:
            if dfs(node_id):
                raise YAMLLoaderError("Workflow contains a cycle")

    @classmethod
    def _validate_port_connections(cls, workflow: DAGWorkflow) -> None:
        for edge in workflow.edges:
            source_node_id, source_port_id = cls._parse_port_ref(edge.source)
            target_node_id, target_port_id = cls._parse_port_ref(edge.target)

            source_node = workflow.nodes[source_node_id]
            target_node = workflow.nodes[target_node_id]

            source_port_exists = any(
                p.id == source_port_id for p in source_node.outputs
            )
            if not source_port_exists:
                raise YAMLLoaderError(f"Source port not found: {edge.source}")

            target_port_exists = any(p.id == target_port_id for p in target_node.inputs)
            if not target_port_exists:
                raise YAMLLoaderError(f"Target port not found: {edge.target}")
