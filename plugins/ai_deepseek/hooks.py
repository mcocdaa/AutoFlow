# @file /plugins/ai_deepseek/hooks.py
# @brief AI DeepSeek 插件 hooks
# @create 2026-03-27

from plugins.ai_deepseek.backend import AIDeepSeekPlugin


def register(registry):
    """AI DeepSeek 插件注册钩子"""
    plugin = AIDeepSeekPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
