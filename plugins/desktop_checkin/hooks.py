# @file /plugins/desktop_checkin/hooks.py
# @brief 桌面打卡插件 hooks
# @create 2026-03-27

from plugins.desktop_checkin.backend import DesktopCheckinPlugin


def register(registry, config=None):
    """桌面打卡插件注册钩子"""
    plugin = DesktopCheckinPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
    for type_name, handler in plugin.checks.items():
        registry.register_check(type_name, handler)
