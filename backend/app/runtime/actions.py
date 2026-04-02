# @file /backend/app/runtime/actions.py
# @brief DAG工作流引擎 - Action注册器与内置Actions实现
# @create 2026-04-01 00:00:00

from __future__ import annotations

import time
from typing import Any, Callable, Dict

from app.core.registry import ActionContext, Registry

ActionHandler = Callable[[ActionContext, Dict[str, Any]], Any]


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: Dict[str, ActionHandler] = {}

    def register(self, action_type: str, handler: ActionHandler) -> None:
        self._actions[action_type] = handler

    def get(self, action_type: str) -> ActionHandler:
        if action_type not in self._actions:
            raise ValueError(f"Action type '{action_type}' not found")
        return self._actions[action_type]

    def list_actions(self) -> list[str]:
        return sorted(self._actions.keys())


def log_action(ctx: ActionContext, params: Dict[str, Any]) -> Dict[str, Any]:
    message = params.get("message", "")
    level = params.get("level", "info")
    print(f"[{level}] {message}")
    return {"logged": True, "message": message, "level": level}


def set_var_action(ctx: ActionContext, params: Dict[str, Any]) -> Dict[str, Any]:
    var_name = params.get("name")
    var_value = params.get("value")
    if not var_name:
        raise ValueError("Variable name is required")
    ctx.vars[var_name] = var_value
    return {"name": var_name, "value": var_value}


def wait_action(ctx: ActionContext, params: Dict[str, Any]) -> Dict[str, Any]:
    seconds = float(params.get("seconds", 1.0))
    if seconds < 0:
        raise ValueError("Seconds must be non-negative")
    time.sleep(seconds)
    return {"waited_seconds": seconds}


def register_builtin_actions(registry: ActionRegistry) -> None:
    registry.register("log", log_action)
    registry.register("set_var", set_var_action)
    registry.register("wait", wait_action)


_global_action_registry: ActionRegistry | None = None


def get_action_registry() -> ActionRegistry:
    global _global_action_registry
    if _global_action_registry is None:
        _global_action_registry = ActionRegistry()
        register_builtin_actions(_global_action_registry)
    return _global_action_registry
