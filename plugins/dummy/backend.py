# @file /plugins/dummy/backend.py
# @brief Dummy 插件：回传用户输入信息（测试用）
# @create 2026-02-21 00:00:00
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext

from plugins.common.plugin import Plugin


class DummyPlugin(Plugin):
    """Dummy 插件：回传用户输入信息（测试用）"""

    name = "dummy"
    version = "0.1.0"
    actions = {"dummy.echo": "_echo"}

    def _echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


PLUGIN = DummyPlugin
