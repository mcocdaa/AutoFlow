from __future__ import annotations

from typing import Any, Callable, ClassVar, Dict, List, Optional

from app.runtime.dag_models import (
    BaseNode,
    DAGWorkflow,
    GroupConfig,
    InputMapping,
    InternalSubgraph,
    OutputMapping,
    SubflowConfig,
)


class GroupNode(BaseNode):
    """分组节点 - 包含内部子图的复合节点"""

    def __init__(
        self,
        id: str,
        name: str = "Group",
        **kwargs,
    ):
        kwargs.pop("type", None)
        kwargs.pop("inputs", None)
        kwargs.pop("outputs", None)
        if "type" not in kwargs:
            kwargs["type"] = "group"
        super().__init__(
            id=id,
            name=name,
            **kwargs,
        )
        self._internal_nodes_cache: Dict[str, Any] = {}

    @property
    def group_config(self) -> GroupConfig:
        """获取分组配置"""
        config_dict = self.config.get("group_config", {})
        return GroupConfig(**config_dict)

    def execute(
        self,
        inputs: Dict[str, Any],
        subgraph_executor: Optional[Callable] = None,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行分组节点，执行内部子图"""
        group_config = self.group_config
        internal_subgraph = group_config.internal_subgraph

        if not internal_subgraph.nodes and not self._internal_nodes_cache:
            return {}

        internal_inputs: Dict[str, Any] = {}
        for mapping in group_config.input_mappings:
            if mapping.external_port_id in inputs:
                internal_port_key = (
                    f"{mapping.internal_node_id}.{mapping.internal_port_id}"
                )
                internal_inputs[internal_port_key] = inputs[mapping.external_port_id]

        internal_outputs: Dict[str, Any] = {}
        if subgraph_executor:
            internal_outputs = subgraph_executor(
                internal_subgraph,
                internal_inputs,
                **handler_kwargs,
            )
        else:
            internal_outputs = self._simple_execute_subgraph(
                internal_subgraph,
                internal_inputs,
            )

        external_outputs: Dict[str, Any] = {}
        for mapping in group_config.output_mappings:
            internal_port_key = f"{mapping.internal_node_id}.{mapping.internal_port_id}"
            if internal_port_key in internal_outputs:
                external_outputs[mapping.external_port_id] = internal_outputs[
                    internal_port_key
                ]

        return external_outputs

    def _simple_execute_subgraph(
        self,
        subgraph: InternalSubgraph,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """简单执行子图（不依赖外部执行器）"""
        outputs: Dict[str, Any] = {}

        nodes_to_execute = (
            self._internal_nodes_cache if self._internal_nodes_cache else subgraph.nodes
        )

        for node_id, node in nodes_to_execute.items():
            node_inputs: Dict[str, Any] = {}
            for port in node.inputs:
                port_key = f"{node_id}.{port.id}"
                if port_key in inputs:
                    node_inputs[port.id] = inputs[port_key]
                elif port.default is not None:
                    node_inputs[port.id] = port.default
            if hasattr(node, "execute"):
                try:
                    node_outputs = node.execute(node_inputs)
                    for port_id, value in node_outputs.items():
                        output_key = f"{node_id}.{port_id}"
                        outputs[output_key] = value
                except Exception:
                    pass
        return outputs


class SubflowNode(BaseNode):
    """子流程节点 - 引用并执行其他工作流"""

    MAX_RECURSION_DEPTH: ClassVar[int] = 10

    def __init__(
        self,
        id: str,
        name: str = "Subflow",
        **kwargs,
    ):
        kwargs.pop("type", None)
        kwargs.pop("inputs", None)
        kwargs.pop("outputs", None)
        if "type" not in kwargs:
            kwargs["type"] = "subflow"
        super().__init__(
            id=id,
            name=name,
            **kwargs,
        )

    @property
    def subflow_config(self) -> SubflowConfig:
        """获取子流程配置"""
        config_dict = self.config.get("subflow_config", {})
        return SubflowConfig(**config_dict)

    def execute(
        self,
        inputs: Dict[str, Any],
        subflow_loader: Optional[Callable] = None,
        subflow_executor: Optional[Callable] = None,
        recursion_stack: Optional[List[str]] = None,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行子流程节点，加载并执行引用的工作流"""
        subflow_config = self.subflow_config

        if recursion_stack is None:
            recursion_stack = []

        if len(recursion_stack) >= self.MAX_RECURSION_DEPTH:
            raise ValueError(f"Max recursion depth {self.MAX_RECURSION_DEPTH} exceeded")

        if subflow_config.subflow_id in recursion_stack:
            raise ValueError(
                f"Circular reference detected: {subflow_config.subflow_id}"
            )

        recursion_stack = recursion_stack + [subflow_config.subflow_id]

        subflow: Optional[DAGWorkflow] = None
        if subflow_loader:
            subflow = subflow_loader(
                subflow_config.subflow_id, subflow_config.subflow_version
            )
        else:
            subflow = self._simple_load_subflow(subflow_config.subflow_id)

        if not subflow:
            raise ValueError(f"Subflow {subflow_config.subflow_id} not found")

        subflow_inputs: Dict[str, Dict[str, Any]] = {}
        for mapping in subflow_config.input_mappings:
            if mapping.external_port_id in inputs:
                internal_port_key = (
                    f"{mapping.internal_node_id}.{mapping.internal_port_id}"
                )
                subflow_inputs[internal_port_key] = inputs[mapping.external_port_id]

        subflow_outputs: Dict[str, Dict[str, Any]] = {}
        if subflow_executor:
            subflow_outputs = subflow_executor(
                subflow,
                subflow_inputs,
                recursion_stack=recursion_stack,
                **handler_kwargs,
            )
        else:
            subflow_outputs = self._simple_execute_subflow(
                subflow,
                subflow_inputs,
            )

        external_outputs: Dict[str, Any] = {}
        for mapping in subflow_config.output_mappings:
            internal_port_key = f"{mapping.internal_node_id}.{mapping.internal_port_id}"
            if internal_port_key in subflow_outputs:
                external_outputs[mapping.external_port_id] = subflow_outputs[
                    internal_port_key
                ]

        return external_outputs

    def _simple_load_subflow(self, subflow_id: str) -> Optional[DAGWorkflow]:
        """简单加载子流程（不依赖外部加载器）"""
        return None

    def _simple_execute_subflow(
        self,
        subflow: DAGWorkflow,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """简单执行子流程（不依赖外部执行器）"""
        outputs: Dict[str, Any] = {}
        for node_id, node in subflow.nodes.items():
            node_inputs: Dict[str, Any] = {}
            for port in node.inputs:
                port_key = f"{node_id}.{port.id}"
                if port_key in inputs:
                    node_inputs[port.id] = inputs[port_key]
                elif port.default is not None:
                    node_inputs[port.id] = port.default
            if hasattr(node, "execute"):
                try:
                    node_outputs = node.execute(node_inputs)
                    for port_id, value in node_outputs.items():
                        output_key = f"{node_id}.{port_id}"
                        outputs[output_key] = value
                except Exception:
                    pass
        return outputs
