# @file /plugins/ai_deepseek/hooks.py
# @brief AI DeepSeek 插件 hooks
# @create 2026-03-27

from app.core.hook_manager import hook_manager

from plugins.ai_deepseek.backend import AIDeepSeekPlugin


@hook_manager.hook("registry_register")
def ai_deepseek_register(registry):
    """AI DeepSeek 插件注册钩子"""
    plugin = AIDeepSeekPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
