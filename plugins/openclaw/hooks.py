# @file /plugins/openclaw/hooks.py
# @brief OpenClaw 插件 hooks
# @create 2026-03-27

from plugins.openclaw.backend import OpenClawPlugin


def register(registry, config=None):
    """OpenClaw 插件注册钩子"""
    plugin = OpenClawPlugin(config)
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
    for type_name, handler in plugin.checks.items():
        registry.register_check(type_name, handler)
