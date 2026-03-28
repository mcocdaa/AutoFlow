# @file /plugins/desktop_checkin/backend.py
# @brief 桌面自动打卡插件后端实现
# @create 2026-03-15 00:00:00

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext


def _is_truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def _dry_run(ctx: ActionContext, params: dict[str, Any]) -> bool:
    if _is_truthy(params.get("dry_run")):
        return True
    if _is_truthy(ctx.vars.get("dry_run")):
        return True
    return _is_truthy(os.getenv("AUTOFLOW_DESKTOP_DRY_RUN"))


def _safe_name(name: str) -> str:
    n = Path(name).name
    n = re.sub(r"[^a-zA-Z0-9._-]+", "_", n)
    return n or "screenshot.png"


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / path).resolve()


class DesktopCheckinPlugin:
    def __init__(self) -> None:
        self.name = "desktop-checkin"
        self.version = "0.1.0"
        self.actions = {
            "desktop.activate_window": self.activate_window,
            "desktop.click": self.click,
            "desktop.double_click": self.double_click,
            "desktop.drag": self.drag,
            "desktop.type_text": self.type_text,
            "desktop.hotkey": self.hotkey,
            "desktop.wait": self.wait,
            "desktop.screenshot": self.screenshot,
        }
        self.checks = {
            "desktop.image_exists": self.image_exists,
            "desktop.window_title_contains": self.window_title_contains,
        }

    def activate_window(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        title = str(params.get("title", ""))
        if not title:
            raise ValueError("title is required")

        timeout_seconds = float(params.get("timeout_seconds", 0))
        use_regex = _is_truthy(params.get("regex"))
        focus = _is_truthy(params.get("focus", True))

        if _dry_run(ctx, params):
            return {"activated": True, "title": title, "regex": use_regex, "focus": focus, "dry_run": True}

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
                return {"activated": True, "title": getattr(match, "title", "") or "", "dry_run": False}

            if time.time() >= deadline:
                return {"activated": False, "title": title, "dry_run": False, "seen_titles": last_titles[:50]}
            time.sleep(0.2)

    def click(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        x = int(params["x"])
        y = int(params["y"])
        button = str(params.get("button", "left"))
        clicks = int(params.get("clicks", 1))
        interval = float(params.get("interval", 0))

        if _dry_run(ctx, params):
            return {"clicked": True, "x": x, "y": y, "button": button, "clicks": clicks, "dry_run": True}

        import pyautogui

        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
        return {"clicked": True, "x": x, "y": y, "button": button, "clicks": clicks, "dry_run": False}

    def double_click(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        params = dict(params)
        params["clicks"] = 2
        return self.click(ctx, params)

    def drag(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        from_x = int(params["from_x"])
        from_y = int(params["from_y"])
        to_x = int(params["to_x"])
        to_y = int(params["to_y"])
        duration = float(params.get("duration", 0))
        button = str(params.get("button", "left"))

        if _dry_run(ctx, params):
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

    def type_text(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        text = str(params.get("text", ""))
        interval = float(params.get("interval", 0))
        secret = _is_truthy(params.get("secret"))

        if _dry_run(ctx, params):
            return {"typed": True, "length": len(text), "secret": secret, "dry_run": True}

        import pyautogui

        pyautogui.typewrite(text, interval=interval)
        if secret:
            return {"typed": True, "length": len(text), "secret": True, "dry_run": False}
        return {"typed": True, "text": text, "secret": False, "dry_run": False}

    def hotkey(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        keys = params.get("keys")
        if not isinstance(keys, list) or not keys:
            raise ValueError("keys must be a non-empty list")
        keys = [str(k) for k in keys]

        if _dry_run(ctx, params):
            return {"sent": True, "keys": keys, "dry_run": True}

        import pyautogui

        pyautogui.hotkey(*keys)
        return {"sent": True, "keys": keys, "dry_run": False}

    def wait(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        seconds = float(params.get("seconds", 0))
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        if not _dry_run(ctx, params):
            time.sleep(seconds)
        return {"waited_seconds": seconds, "dry_run": _dry_run(ctx, params)}

    def screenshot(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        name = _safe_name(str(params.get("name", "screenshot.png")))
        region = params.get("region")
        fmt = str(params.get("format", "png")).lower()
        if fmt != "png":
            raise ValueError("only png is supported")

        out_dir = ctx.artifacts_dir / "screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / name

        if _dry_run(ctx, params):
            try:
                from PIL import Image

                Image.new("RGB", (1, 1), color=(0, 0, 0)).save(out_path, format="PNG")
            except Exception:
                out_path.write_bytes(b"")
            return {"saved": True, "path": str(out_path.relative_to(ctx.artifacts_dir)), "dry_run": True}

        import pyautogui

        if region is not None:
            if not isinstance(region, list) or len(region) != 4:
                raise ValueError("region must be [left, top, width, height]")
            region_tuple = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        else:
            region_tuple = None

        img = pyautogui.screenshot(region=region_tuple)
        img.save(out_path)
        return {"saved": True, "path": str(out_path.relative_to(ctx.artifacts_dir)), "dry_run": False}

    def image_exists(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
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
                    found = pyautogui.locateOnScreen(str(template), confidence=float(confidence))
            except Exception:
                found = None
            if found is not None:
                return True
            if time.time() >= deadline:
                return False
            time.sleep(0.2)

    def window_title_contains(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
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


def register() -> DesktopCheckinPlugin:
    return DesktopCheckinPlugin()
