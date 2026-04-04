"""节点元数据 API - 返回所有已注册节点类型的端口定义和展示信息

前端在启动时调用 GET /v2/nodes 拉取一次，缓存后替代硬编码的 node-defaults.ts。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.node_registry import node_registry

router = APIRouter()


@router.get("/nodes", summary="获取所有节点类型元数据")
def list_nodes() -> list[dict[str, Any]]:
    """返回所有已注册节点类型的元数据列表，包含端口定义、图标、颜色和配置 schema。

    前端用此接口替代硬编码的 node-defaults.ts 和 node-templates.ts。
    插件注册的自定义节点类型自动包含在结果中。
    """
    return [meta.to_dict() for meta in node_registry.all()]


@router.get("/nodes/{node_type}", summary="获取指定节点类型元数据")
def get_node(node_type: str) -> dict[str, Any]:
    """返回指定节点类型的元数据。"""
    meta = node_registry.get(node_type)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"节点类型 '{node_type}' 未注册")
    return meta.to_dict()
