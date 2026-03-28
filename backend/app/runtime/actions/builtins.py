# @file /backend/app/runtime/actions/builtins.py
# @brief 内置 Action/Check（最小集合）
# @create 2026-02-21 00:00:00

from __future__ import annotations

import time
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry


def _action_core_log(ctx: ActionContext, params: dict[str, Any]) -> Any:
    message = params.get("message")
    return {"message": message, "run_id": ctx.run_id, "step_id": ctx.step_id}


def _action_core_sleep(ctx: ActionContext, params: dict[str, Any]) -> Any:
    seconds = float(params.get("seconds", 0))
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    time.sleep(seconds)
    return {"slept_seconds": seconds}


def _check_core_always_true(ctx: CheckContext, params: dict[str, Any]) -> bool:
    return True


def _check_text_contains(ctx: CheckContext, params: dict[str, Any]) -> bool:
    needle = params.get("needle")
    if needle is None:
        raise ValueError("needle is required")
    haystack = ctx.action_output
    if haystack is None:
        return False
    if isinstance(haystack, (dict, list)):
        haystack_str = str(haystack)
    else:
        haystack_str = str(haystack)
    return str(needle) in haystack_str


def register_builtins(registry: Registry) -> None:
    registry.register_plugin(name="builtin", version="0.1.0")

    registry.register_action("core.log", _action_core_log)
    registry.register_action("core.sleep", _action_core_sleep)

    registry.register_check("core.always_true", _check_core_always_true)
    registry.register_check("text.contains", _check_text_contains)
