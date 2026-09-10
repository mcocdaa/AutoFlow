# @file /plugins/examples/hello_world.py
# @brief 示例插件：注册 core.hello action
# @create 2026-08-09
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class HelloWorldPlugin(Plugin):
    """示例插件：注册 core.hello action"""

    name = "hello-world"
    version = "1.0.0"
    actions = {"core.hello": "_hello"}

    def _hello(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        name = params.get("name", "World")
        return {"message": f"Hello, {name} from AutoFlow!"}


PLUGIN = HelloWorldPlugin
