# @file /backend/app/api/v1/routes/plugins.py
# @brief 插件与可用 Action/Check 列表
# @create 2026-02-21 00:00:00
# @update 2026-03-30 添加节点模板 API

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.plugin.models import PluginErrorItem, PluginItem, PluginsResponse
from app.runtime import get_registry

router = APIRouter()


class NodeTemplate(BaseModel):
    """节点模板模型"""

    type: str
    label: str
    category: str
    icon: str
    description: Optional[str] = None
    default_config: Dict[str, Any] = Field(default_factory=dict)


class NodeTemplatesResponse(BaseModel):
    """节点模板列表响应"""

    templates: List[NodeTemplate]


@router.get("/plugins", response_model=PluginsResponse)
def list_plugins() -> PluginsResponse:
    registry = get_registry()
    plugins = [
        PluginItem(name=p.name, version=p.version) for p in registry.list_plugins()
    ]
    errors = [
        PluginErrorItem(plugin_id=e.plugin_id, file_path=e.file_path, error=e.error)
        for e in registry.list_plugin_errors()
    ]
    return PluginsResponse(
        plugins=plugins,
        actions=registry.list_actions(),
        checks=registry.list_checks(),
        errors=errors,
    )


@router.get("/plugins/node-templates", response_model=NodeTemplatesResponse)
def get_node_templates() -> NodeTemplatesResponse:
    """获取节点模板列表（基于注册的 Actions）"""
    registry = get_registry()
    actions = registry.list_actions()

    templates = [
        NodeTemplate(
            type="start",
            label="开始",
            category="basic",
            icon="play-circle",
            description="工作流起始节点",
            default_config={},
        ),
        NodeTemplate(
            type="output",
            label="输出",
            category="basic",
            icon="export",
            description="工作流输出节点",
            default_config={},
        ),
        NodeTemplate(
            type="condition",
            label="条件分支",
            category="logic",
            icon="swap",
            description="条件判断节点",
            default_config={"condition": ""},
        ),
        NodeTemplate(
            type="loop",
            label="循环",
            category="logic",
            icon="reload",
            description="循环执行节点",
            default_config={"forEach": "", "forItemVar": "item"},
        ),
        NodeTemplate(
            type="python",
            label="Python 脚本",
            category="custom",
            icon="code",
            description="执行 Python 代码",
            default_config={"code": ""},
        ),
    ]

    for action_type in actions:
        if action_type.startswith("ai_"):
            category = "ai"
            icon = "robot"
        elif action_type.startswith("http_") or action_type.startswith("api_"):
            category = "io"
            icon = "link"
        else:
            category = "custom"
            icon = "appstore"

        templates.append(
            NodeTemplate(
                type=action_type,
                label=action_type.replace("_", " ").title(),
                category=category,
                icon=icon,
                description=f"执行 {action_type} 动作",
                default_config={},
            )
        )

    return NodeTemplatesResponse(templates=templates)
