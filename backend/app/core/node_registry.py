"""Node Registry - 节点元数据注册表

前端通过 GET /v2/nodes 获取所有节点类型的端口定义、展示信息和配置 schema，
插件通过 node_meta_register hook 注入自定义节点，无需修改任何前端代码。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PortMeta:
    """端口元数据"""

    id: str
    name: str
    type: str = "any"  # "any" | "string" | "number" | "boolean" | "object" | "array"
    required: bool = False


@dataclass
class NodeMeta:
    """节点元数据 - 前端展示和端口定义的唯一来源"""

    type: str
    label: str
    category: str  # "core" | "control" | "data" | "io" | "composite" | "action"
    icon: str
    color: str
    inputs: list[PortMeta] = field(default_factory=list)
    outputs: list[PortMeta] = field(default_factory=list)
    error_port: PortMeta | None = None
    config_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class NodeRegistry:
    """节点注册表 - 全局单例，管理所有已知节点类型"""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeMeta] = {}

    def register(self, meta: NodeMeta) -> None:
        """注册节点元数据。同名节点会被覆盖（插件可覆盖内置节点的展示信息）。"""
        if meta.type in self._nodes:
            logger.debug(f"[NodeRegistry] 覆盖节点元数据: {meta.type}")
        self._nodes[meta.type] = meta

    def all(self) -> list[NodeMeta]:
        """返回所有已注册节点，按 category 和 type 排序。"""
        return sorted(self._nodes.values(), key=lambda m: (m.category, m.type))

    def get(self, node_type: str) -> NodeMeta | None:
        """按类型获取节点元数据。"""
        return self._nodes.get(node_type)

    def __len__(self) -> int:
        return len(self._nodes)


# 全局单例
node_registry = NodeRegistry()
