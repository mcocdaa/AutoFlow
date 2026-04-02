# @file /plugins/desktop_checkin/hooks.py
# @brief 桌面打卡插件 hooks
# @create 2026-03-27

from app.core.hook_manager import hook_manager

from plugins.desktop_checkin.backend import DesktopCheckinPlugin


@hook_manager.hook("registry_register")
def desktop_checkin_register(registry):
    """桌面打卡插件注册钩子"""
    plugin = DesktopCheckinPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
    for type_name, handler in plugin.checks.items():
        registry.register_check(type_name, handler)
