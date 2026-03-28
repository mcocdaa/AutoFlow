# @file /backend/app/plugin/__init__.py
# @brief 插件系统模块（向后兼容）
# @create 2026-03-15
# @update 2026-03-27 重构为基于 Hook 的插件系统

from app.core.registry import (
    ActionContext,
    CheckContext,
    PluginInfo,
    PluginLoadErrorInfo,
    Registry,
)
from app.plugin.models import PluginErrorItem, PluginItem, PluginsResponse

__all__ = [
    "PluginItem",
    "PluginErrorItem",
    "PluginsResponse",
    "ActionContext",
    "CheckContext",
    "PluginInfo",
    "PluginLoadErrorInfo",
    "Registry",
]
