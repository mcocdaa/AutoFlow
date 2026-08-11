# @file /plugins/common/plugin.py
# @brief Plugin 抽象基类:声明式元信息 + 统一注册(替代 hooks.py 样板)
# @create 2026-08-10

from __future__ import annotations

from typing import Any

from app.core.registry import ActionHandler, CheckHandler, Registry


class Plugin:
    """插件基类:声明式元信息 + 统一注册"""

    name: str
    version: str = "0.1.0"
    actions: dict[str, ActionHandler] = {}
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def register(self, registry: Registry) -> None:
        """注册 plugin 元信息、actions、checks(替代 hooks.py 样板)"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)
