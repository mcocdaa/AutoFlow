# @file /backend/app/api/v1/routes/plugins.py
# @brief 插件与可用 Action/Check 列表
# @create 2026-02-21 00:00:00

from __future__ import annotations

from fastapi import APIRouter

from app.plugin.models import PluginErrorItem, PluginItem, PluginsResponse
from app.runtime import get_registry

router = APIRouter()


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
