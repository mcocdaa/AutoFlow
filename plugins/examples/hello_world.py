# @file /plugins/examples/hello_world.py
# @brief 示例插件：注册 core.hello action
# @create 2026-08-09
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _hello(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = params.get("name", "World")
    return {"message": f"Hello, {name} from AutoFlow!"}


class HelloWorldPlugin(Plugin):
    """示例插件：注册 core.hello action"""

    name = "hello-world"
    version = "1.0.0"
    actions = {
        "core.hello": _hello,
    }
    checks = {}


PLUGIN = HelloWorldPlugin
