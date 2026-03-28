# @file /plugins/dummy/backend.py
# @brief Dummy 插件：回传用户输入信息（测试用）
# @create 2026-02-21 00:00:00
# @update 2026-03-27 更新为基于 Hook 的插件系统

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext


class DummyPlugin:
    def __init__(self) -> None:
        self.name = "dummy"
        self.version = "0.1.0"
        self.actions = {
            "dummy.echo": self.echo,
        }
        self.checks = {}

    def echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }
