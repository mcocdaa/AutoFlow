# @file /backend/app/core/__init__.py
# @brief Core 模块导出
# @create 2026-03-27

# isort: off
from app.core.setting_manager import SettingManager, setting_manager
from app.core.hook_manager import HookManager, hook_manager
from app.core.registry import ActionContext, CheckContext, Registry, registry
from app.core.plugin_manager import PluginManager, plugin_manager

# isort: on
