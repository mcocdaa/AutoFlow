# @file /plugins/common/__init__.py
# @brief 插件共享代码:导出 Plugin 基类与 helpers(不注册进 plugins.yaml)
# @create 2026-08-10

from plugins.common.helpers import (
    is_truthy,
    read_text,
    safe_name,
    utc_now_iso,
    write_text,
)
from plugins.common.plugin import Plugin

__all__ = [
    "Plugin",
    "is_truthy",
    "read_text",
    "safe_name",
    "utc_now_iso",
    "write_text",
]
