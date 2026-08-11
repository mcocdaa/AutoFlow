# @file /plugins/desktop_checkin/backend.py
# @brief 桌面自动打卡插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext

from plugins.common.helpers import dry_run_enabled, is_truthy, safe_name
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_DESKTOP_DRY_RUN"


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / path).resolve()


def _activate_window(ctx: ActionContext, params: dict[str, Any]) -> Any:
    title = str(params.get("title", ""))
    if not title:
        raise ValueError("title is required")

    timeout_seconds = float(params.get("timeout_seconds", 0))
    use_regex = is_truthy(params.get("regex"))
    focus = is_truthy(params.get("focus", True))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "activated": True,
            "title": title,
            "regex": use_regex,
            "focus": focus,
            "dry_run": True,
        }

    try:
        import pygetwindow as gw
    except Exception as e:
        raise RuntimeError(f"pygetwindow unavailable: {e}") from e

    deadline = time.time() + max(0.0, timeout_seconds)
    last_titles: list[str] = []
    while True:
        try:
            windows = gw.getAllWindows()
        except Exception:
            windows = []

        match = None
        if use_regex:
            pattern = re.compile(title)
            for w in windows:
                t = getattr(w, "title", "") or ""
                if pattern.search(t):
                    match = w
                    break
        else:
            for w in windows:
                t = getattr(w, "title", "") or ""
                if title in t:
                    match = w
                    break

        last_titles = [getattr(w, "title", "") or "" for w in windows]
        if match is not None:
            if focus:
                try:
                    match.activate()
                except Exception:
                    pass
            return {
                "activated": True,
                "title": getattr(match, "title", "") or "",
                "dry_run": False,
            }

        if time.time() >= deadline:
            return {
                "activated": False,
                "title": title,
                "dry_run": False,
                "seen_titles": last_titles[:50],
            }
        time.sleep(0.2)


def _click(ctx: ActionContext, params: dict[str, Any]) -> Any:
    x = int(params["x"])
    y = int(params["y"])
    button = str(params.get("button", "left"))
    clicks = int(params.get("clicks", 1))
    interval = float(params.get("interval", 0))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "clicked": True,
            "x": x,
            "y": y,
            "button": button,
            "clicks": clicks,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    return {
        "clicked": True,
        "x": x,
        "y": y,
        "button": button,
        "clicks": clicks,
        "dry_run": False,
    }


def _double_click(ctx: ActionContext, params: dict[str, Any]) -> Any:
    params = dict(params)
    params["clicks"] = 2
    return _click(ctx, params)


def _drag(ctx: ActionContext, params: dict[str, Any]) -> Any:
    from_x = int(params["from_x"])
    from_y = int(params["from_y"])
    to_x = int(params["to_x"])
    to_y = int(params["to_y"])
    duration = float(params.get("duration", 0))
    button = str(params.get("button", "left"))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "dragged": True,
            "from": {"x": from_x, "y": from_y},
            "to": {"x": to_x, "y": to_y},
            "duration": duration,
            "button": button,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.moveTo(from_x, from_y)
    pyautogui.dragTo(to_x, to_y, duration=duration, button=button)
    return {
        "dragged": True,
        "from": {"x": from_x, "y": from_y},
        "to": {"x": to_x, "y": to_y},
        "duration": duration,
        "button": button,
        "dry_run": False,
    }


def _type_text(ctx: ActionContext, params: dict[str, Any]) -> Any:
    text = str(params.get("text", ""))
    interval = float(params.get("interval", 0))
    secret = is_truthy(params.get("secret"))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "typed": True,
            "length": len(text),
            "secret": secret,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.typewrite(text, interval=interval)
    if secret:
        return {
            "typed": True,
            "length": len(text),
            "secret": True,
            "dry_run": False,
        }
    return {"typed": True, "text": text, "secret": False, "dry_run": False}


def _hotkey(ctx: ActionContext, params: dict[str, Any]) -> Any:
    keys = params.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a non-empty list")
    keys = [str(k) for k in keys]

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {"sent": True, "keys": keys, "dry_run": True}

    import pyautogui

    pyautogui.hotkey(*keys)
    return {"sent": True, "keys": keys, "dry_run": False}


def _wait(ctx: ActionContext, params: dict[str, Any]) -> Any:
    seconds = float(params.get("seconds", 0))
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    dry_run = dry_run_enabled(ctx, params, _DRY_RUN_ENV)
    if not dry_run:
        time.sleep(seconds)
    return {"waited_seconds": seconds, "dry_run": dry_run}


def _screenshot(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = safe_name(
        str(params.get("name", "screenshot.png")), fallback="screenshot.png"
    )
    region = params.get("region")
    fmt = str(params.get("format", "png")).lower()
    if fmt != "png":
        raise ValueError("only png is supported")

    out_dir = ctx.artifacts_dir / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        try:
            from PIL import Image

            Image.new("RGB", (1, 1), color=(0, 0, 0)).save(out_path, format="PNG")
        except Exception:
            out_path.write_bytes(b"")
        return {
            "saved": True,
            "path": str(out_path.relative_to(ctx.artifacts_dir)),
            "dry_run": True,
        }

    import pyautogui

    if region is not None:
        if not isinstance(region, list) or len(region) != 4:
            raise ValueError("region must be [left, top, width, height]")
        region_tuple = (
            int(region[0]),
            int(region[1]),
            int(region[2]),
            int(region[3]),
        )
    else:
        region_tuple = None

    img = pyautogui.screenshot(region=region_tuple)
    img.save(out_path)
    return {
        "saved": True,
        "path": str(out_path.relative_to(ctx.artifacts_dir)),
        "dry_run": False,
    }


def _image_exists(ctx: CheckContext, params: dict[str, Any]) -> bool:
    template_path = params.get("template_path")
    if template_path is None:
        raise ValueError("template_path is required")
    timeout_seconds = float(params.get("timeout_seconds", 0))
    confidence = params.get("confidence")

    deadline = time.time() + max(0.0, timeout_seconds)
    import pyautogui

    template = _resolve_path(str(template_path))

    while True:
        try:
            if confidence is None:
                found = pyautogui.locateOnScreen(str(template))
            else:
                found = pyautogui.locateOnScreen(
                    str(template), confidence=float(confidence)
                )
        except Exception:
            found = None
        if found is not None:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.2)


def _window_title_contains(ctx: CheckContext, params: dict[str, Any]) -> bool:
    needle = str(params.get("needle", ""))
    if not needle:
        raise ValueError("needle is required")
    try:
        import pygetwindow as gw
    except Exception:
        return False
    try:
        w = gw.getActiveWindow()
    except Exception:
        w = None
    title = getattr(w, "title", "") if w is not None else ""
    return needle in (title or "")


class DesktopCheckinPlugin(Plugin):
    """桌面自动打卡插件"""

    name = "desktop-checkin"
    version = "0.1.0"
    actions = {
        "desktop.activate_window": _activate_window,
        "desktop.click": _click,
        "desktop.double_click": _double_click,
        "desktop.drag": _drag,
        "desktop.type_text": _type_text,
        "desktop.hotkey": _hotkey,
        "desktop.wait": _wait,
        "desktop.screenshot": _screenshot,
    }
    checks = {
        "desktop.image_exists": _image_exists,
        "desktop.window_title_contains": _window_title_contains,
    }


PLUGIN = DesktopCheckinPlugin
