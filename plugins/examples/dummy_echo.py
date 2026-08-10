# @file /plugins/examples/dummy_echo.py
# @brief 示例插件：注册 dummy.echo action,回传用户输入信息
# @create 2026-02-21 00:00:00
# @update 2026-08-09 对齐新约定 register(registry)

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext, Registry


def _echo(ctx: ActionContext, params: dict[str, Any]) -> Any:
    return {
        "input": ctx.input,
        "message": params.get("message"),
        "vars": ctx.vars,
    }


def register(registry: Registry, config: dict = None) -> None:
    """注册插件信息与 action(新约定: 接收 registry 并直接注册)"""
    registry.register_plugin(name="dummy-echo", version="0.1.0")
    registry.register_action("dummy.echo", _echo)
