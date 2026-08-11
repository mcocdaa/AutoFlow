# @file /plugins/openclaw/__init__.py
# @brief openclaw 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.openclaw.backend import PLUGIN

__all__ = ["PLUGIN"]
