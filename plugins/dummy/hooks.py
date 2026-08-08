# @file /plugins/dummy/hooks.py
# @brief Dummy 插件 hooks
# @create 2026-03-27

from plugins.dummy.backend import DummyPlugin


def register(registry):
    """Dummy 插件注册钩子"""
    plugin = DummyPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
