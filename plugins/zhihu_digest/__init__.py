# @file /plugins/zhihu_digest/__init__.py
# @brief 知乎摘要插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.zhihu_digest.backend import PLUGIN
from plugins.zhihu_digest.hooks import register

__all__ = ["PLUGIN", "register"]
