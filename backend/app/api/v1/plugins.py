# @file /backend/app/api/v1/routes/plugins.py
# @brief 插件与可用 Action/Check 列表
# @create 2026-02-21 00:00:00
# @update 2026-08-10 映射收敛为 from_info 工厂调用

from __future__ import annotations

from app.plugin.models import PluginErrorItem, PluginItem, PluginsResponse
from app.runtime import get_registry
from fastapi import APIRouter

router = APIRouter()


@router.get("/plugins", response_model=PluginsResponse)
def list_plugins() -> PluginsResponse:
    registry = get_registry()
    plugins = [PluginItem.from_info(p) for p in registry.list_plugins()]
    errors = [PluginErrorItem.from_info(e) for e in registry.list_plugin_errors()]
    return PluginsResponse(
        plugins=plugins,
        actions=registry.list_actions(),
        checks=registry.list_checks(),
        errors=errors,
    )
