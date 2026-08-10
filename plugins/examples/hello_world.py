# @file /plugins/examples/hello_world.py
# @brief 示例插件：注册 core.hello action
# @create 2026-08-09
# @update 2026-08-09 对齐新约定 register(registry)

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext, Registry


def _hello(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = params.get("name", "World")
    return {"message": f"Hello, {name} from AutoFlow!"}


def register(registry: Registry) -> None:
    """注册插件信息与 action(新约定: 接收 registry 并直接注册)"""
    registry.register_plugin(name="hello-world", version="1.0.0")
    registry.register_action("core.hello", _hello)
