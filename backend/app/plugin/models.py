# @file /backend/app/plugin/models.py
# @brief 插件相关的 Pydantic 模型
# @create 2026-02-21 00:00:00
# @update 2026-08-10 新增 from_info 工厂方法,收敛 api 层映射样板

from __future__ import annotations

from app.core.registry import PluginInfo, PluginLoadErrorInfo
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
