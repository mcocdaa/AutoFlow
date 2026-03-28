# @file /plugins/zhihu_digest/hooks.py
# @brief 知乎摘要插件 hooks
# @create 2026-03-27

from app.core.hook_manager import hook_manager
from plugins.zhihu_digest.backend import ZhihuDigestPlugin


@hook_manager.hook("registry_register")
def zhihu_digest_register(registry):
    """知乎摘要插件注册钩子"""
    plugin = ZhihuDigestPlugin()
    registry.register_plugin(plugin.name, plugin.version)
    for type_name, handler in plugin.actions.items():
        registry.register_action(type_name, handler)
