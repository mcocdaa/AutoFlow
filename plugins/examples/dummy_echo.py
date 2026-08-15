# @file /plugins/examples/dummy_echo.py
# @brief 示例插件：注册 dummy.echo action,回传用户输入信息
# @create 2026-02-21 00:00:00
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class DummyEchoPlugin(Plugin):
    """示例插件：注册 dummy.echo action"""

    name = "dummy-echo"
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "dummy.echo": self._echo,
        }
        self.checks = {}

    def _echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


PLUGIN = DummyEchoPlugin
