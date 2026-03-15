# @file /plugins/examples/dummy_echo.py
# @brief Dummy 插件：回传用户输入信息
# @create 2026-02-21 00:00:00

from __future__ import annotations

from typing import Any

from app.plugin.registry import ActionContext


class DummyEchoPlugin:
    def __init__(self) -> None:
        self.name = "dummy-echo"
        self.version = "0.1.0"
        self.actions = {
            "dummy.echo": self.echo,
        }

    def echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


def register() -> DummyEchoPlugin:
    return DummyEchoPlugin()
