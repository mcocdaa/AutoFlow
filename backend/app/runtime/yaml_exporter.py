from __future__ import annotations

from typing import Any, Dict, List

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
    MergeNode,
    PassNode,
    RetryNode,
    SplitNode,
    StartNode,
    SubflowNode,
    SwitchNode,
    WhileNode,
)


class YAMLExporter:
    VERSION = "2.0"

    @classmethod
    def export(cls, workflow: DAGWorkflow) -> str:
        data = cls._build_data(workflow)
        return yaml.dump(data, sort_keys=False, allow_unicode=True, indent=2)

    @classmethod
    def _build_data(cls, workflow: DAGWorkflow) -> Dict[str, Any]:
        return {
            "version": cls.VERSION,
            "name": workflow.name,
            "description": workflow.description,
            "inputs": workflow.inputs,
            "nodes": cls._build_nodes(workflow.nodes),
            "edges": cls._build_edges(workflow.edges),
        }

    @classmethod
    def _build_nodes(cls, nodes: Dict[str, BaseNode]) -> Dict[str, Any]:
        nodes_data: Dict[str, Any] = {}
        for node_id, node in nodes.items():
            nodes_data[node_id] = cls._build_node(node)
        return nodes_data

    @classmethod
    def _build_node(cls, node: BaseNode) -> Dict[str, Any]:
        node_data: Dict[str, Any] = {
            "type": node.type,
            "name": node.name,
        }

        if node.retry and (node.retry.attempts > 0 or node.retry.backoff_seconds > 0):
            node_data["retry"] = {
                "attempts": node.retry.attempts,
                "backoff_seconds": node.retry.backoff_seconds,
            }

        if node.config:
            node_data["config"] = node.config

        if node.inputs:
            node_data["inputs"] = cls._build_input_ports(node.inputs)

        if node.outputs:
            node_data["outputs"] = cls._build_output_ports(node.outputs)

        if node.metadata:
            node_data["metadata"] = node.metadata

        if isinstance(node, (GroupNode, SubflowNode)):
            node_data = cls._add_composite_node_data(node_data, node)

        return node_data

    @classmethod
    def _add_composite_node_data(
        cls, node_data: Dict[str, Any], node: GroupNode | SubflowNode
    ) -> Dict[str, Any]:
        if isinstance(node, GroupNode):
            group_config = node.group_config
            inner_nodes = cls._build_nodes(group_config.internal_subgraph.nodes)
            inner_edges = cls._build_edges(group_config.internal_subgraph.edges)
            port_mapping = {
                "inputs": [m.model_dump() for m in group_config.input_mappings],
                "outputs": [m.model_dump() for m in group_config.output_mappings],
            }
            node_data["inner_nodes"] = inner_nodes
            node_data["inner_edges"] = inner_edges
            node_data["port_mapping"] = port_mapping
        else:
            subflow_config = node.subflow_config
            inner_nodes = (
                cls._build_nodes(subflow_config.internal_subgraph.nodes)
                if hasattr(subflow_config, "internal_subgraph")
                else {}
            )
            inner_edges = (
                cls._build_edges(subflow_config.internal_subgraph.edges)
                if hasattr(subflow_config, "internal_subgraph")
                else []
            )
            port_mapping = {
                "inputs": [m.model_dump() for m in subflow_config.input_mappings],
                "outputs": [m.model_dump() for m in subflow_config.output_mappings],
            }
            node_data["subflow_id"] = subflow_config.subflow_id
            if subflow_config.subflow_version:
                node_data["subflow_version"] = subflow_config.subflow_version
            node_data["inner_nodes"] = inner_nodes
            node_data["inner_edges"] = inner_edges
            node_data["port_mapping"] = port_mapping

        return node_data

    @classmethod
    def _build_input_ports(cls, ports: List[InputPort]) -> List[Dict[str, Any]]:
        return [port.model_dump(exclude_none=True) for port in ports]

    @classmethod
    def _build_output_ports(cls, ports: List[OutputPort]) -> List[Dict[str, Any]]:
        return [port.model_dump(exclude_none=True) for port in ports]

    @classmethod
    def _build_edges(cls, edges: List[Edge]) -> List[Dict[str, Any]]:
        edges_data = []
        for edge in edges:
            edge_data = {
                "source": edge.source,
                "target": edge.target,
            }
            if edge.id:
                edge_data["id"] = edge.id
            edges_data.append(edge_data)
        return edges_data
