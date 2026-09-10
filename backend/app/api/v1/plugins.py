# @file /backend/app/api/v1/plugins.py
# @brief 插件与可用 Action/Check 列表(含响应模型)
# @create 2026-02-21 00:00:00
# @update 2026-08-22 吸收原 app/plugin/models.py,删除 shim 包

from __future__ import annotations

from app.core.registry import PluginInfo, PluginLoadErrorInfo
from app.runtime import get_registry
from fastapi import APIRouter
from pydantic import BaseModel


class PluginItem(BaseModel):
    name: str
    version: str

    @classmethod
    def from_info(cls, info: PluginInfo) -> PluginItem:
        """从 registry.PluginInfo 构造"""
        return cls(name=info.name, version=info.version)


class PluginErrorItem(BaseModel):
    plugin_id: str
    file_path: str
    error: str

    @classmethod
    def from_info(cls, info: PluginLoadErrorInfo) -> PluginErrorItem:
        """从 registry.PluginLoadErrorInfo 构造"""
        return cls(
            plugin_id=info.plugin_id,
            file_path=info.file_path,
            error=info.error,
        )


class PluginsResponse(BaseModel):
    plugins: list[PluginItem]
    actions: list[str]
    checks: list[str]
    errors: list[PluginErrorItem]


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
