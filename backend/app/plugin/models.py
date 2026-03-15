# @file /backend/app/plugin/models.py
# @brief 插件相关的 Pydantic 模型
# @create 2026-02-21 00:00:00

from __future__ import annotations

from pydantic import BaseModel


class PluginItem(BaseModel):
    name: str
    version: str


class PluginErrorItem(BaseModel):
    plugin_id: str
    file_path: str
    error: str


class PluginsResponse(BaseModel):
    plugins: list[PluginItem]
    actions: list[str]
    checks: list[str]
    errors: list[PluginErrorItem]
