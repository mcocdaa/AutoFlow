# @file /plugins/dummy/hooks.py
# @brief Dummy 插件 hooks
# @create 2026-03-27

from app.core.hook_manager import hook_manager

from plugins.dummy.backend import DummyPlugin


@hook_manager.hook("registry_register")
def dummy_register(registry):
    """Dummy 插件注册钩子"""
    plugin = DummyPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
