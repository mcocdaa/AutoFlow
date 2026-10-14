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
    return str(needle) in str(haystack)


def _check_core_assert_truthy(ctx: CheckContext, params: dict[str, Any]) -> bool:
    val = params["value"] if "value" in params else ctx.action_output
    if isinstance(val, str):
        stripped = val.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            return False
        return stripped.lower() not in ("", "false", "0", "none", "null", "no")
    return bool(val)


def _check_core_assert_equals(ctx: CheckContext, params: dict[str, Any]) -> bool:
    if "actual" in params:
        actual = params["actual"]
    elif "left" in params:
        actual = params["left"]
    elif "value" in params and "expected" in params:
        actual = params["value"]
    elif ("key" in params or "field" in params) and isinstance(ctx.action_output, dict):
        field = str(params.get("key") or params.get("field"))
        actual = ctx.action_output.get(field)
    else:
        actual = ctx.action_output

    if "expected" in params:
        expected = params["expected"]
    elif "right" in params:
        expected = params["right"]
    elif "value" in params:
        expected = params["value"]
    else:
        raise ValueError("expected is required")

    return actual == expected


def _check_core_assert_status(ctx: CheckContext, params: dict[str, Any]) -> bool:
    expected = params.get(
        "expected_status",
        params.get("expected", params.get("status", params.get("status_code", 200))),
    )
    if "actual" in params or "value" in params:
        actual = params.get("actual", params.get("value"))
    elif isinstance(ctx.action_output, dict):
        actual = ctx.action_output.get("status_code", ctx.action_output.get("status"))
    else:
        actual = ctx.action_output

    if actual is None:
        return False
    if isinstance(expected, list):
        return actual in expected
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return actual == expected


def register_builtins(registry: Registry) -> None:
    registry.register_plugin(name="builtin", version="0.1.0")

    registry.register_action("core.log", _action_core_log)
    registry.register_action("core.sleep", _action_core_sleep)

    registry.register_check("core.always_true", _check_core_always_true)
    registry.register_check("text.contains", _check_text_contains)
    registry.register_check("core.assert_truthy", _check_core_assert_truthy)
    registry.register_check("core.assert_equals", _check_core_assert_equals)
    registry.register_check("core.assert_status", _check_core_assert_status)
