# @file /plugins/zhihu_digest/__init__.py
# @brief zhihu_digest 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.zhihu_digest.backend import PLUGIN

__all__ = ["PLUGIN"]
