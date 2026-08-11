# @file /plugins/desktop_checkin/__init__.py
# @brief desktop_checkin 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.desktop_checkin.backend import PLUGIN

__all__ = ["PLUGIN"]
