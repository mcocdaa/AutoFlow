# @file /backend/app/plugin/__init__.py
# @brief 插件系统模块
# @create 2026-03-15

from app.plugin.models import PluginErrorItem, PluginItem, PluginsResponse
from app.plugin.registry import ActionContext, CheckContext, PluginInfo, PluginLoadErrorInfo, Registry
from app.plugin.plugin_loader import load_plugins_into_registry

__all__ = [
    "PluginItem",
    "PluginErrorItem",
    "PluginsResponse",
    "ActionContext",
    "CheckContext",
    "PluginInfo",
    "PluginLoadErrorInfo",
    "Registry",
    "load_plugins_into_registry",
]
