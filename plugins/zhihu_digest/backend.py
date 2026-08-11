# @file /plugins/zhihu_digest/backend.py
# @brief 知乎回答总结插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.core.registry import ActionContext

from plugins.common.helpers import dry_run_enabled, read_text, utc_now_iso, write_text
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_ZHIHU_DRY_RUN"


def _parse_answer_url(url: str) -> tuple[str | None, str | None]:
    m = re.search(r"/question/(\d+)/answer/(\d+)", url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _get_cookie(params: dict[str, Any]) -> str | None:
    cookie = params.get("cookie")
    if isinstance(cookie, str) and cookie.strip():
        if cookie.startswith("env:"):
            return os.getenv(cookie[4:]) or None
        return cookie

    env_name = params.get("cookie_env")
    if isinstance(env_name, str) and env_name.strip():
        return os.getenv(env_name) or None

    return os.getenv("ZHIHU_COOKIE") or None


def _fetch_answer(ctx: ActionContext, params: dict[str, Any]) -> Any:
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url is required")

    question_id, answer_id = _parse_answer_url(url)
    if question_id is None or answer_id is None:
        raise ValueError("unsupported zhihu answer url")

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        answer_text = '点赞后弹出来的"已赞同"可以上下拖动。'
        rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", answer_text)
        return {
            "question_id": question_id,
            "answer_id": answer_id,
            "question_title": None,
            "answer_text_path": rel,
            "source_url": url,
            "fetched_at": utc_now_iso(),
            "dry_run": True,
        }

    mode = str(params.get("mode", "auto")).lower()
    timeout_seconds = float(params.get("timeout_seconds", 30))
    cookie = _get_cookie(params)

    if mode in {"auto", "playwright"}:
        return _fetch_answer_playwright(
            ctx=ctx,
            url=url,
            question_id=question_id,
            answer_id=answer_id,
            timeout_seconds=timeout_seconds,
            cookie=cookie,
        )
    raise ValueError(f"unsupported mode: {mode}")


def _fetch_answer_playwright(
    *,
    ctx: ActionContext,
    url: str,
    question_id: str,
    answer_id: str,
    timeout_seconds: float,
    cookie: str | None,
) -> Any:
    # 优先用 answer_id 定位目标回答的选择器,失败时回退到通用选择器
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(f"playwright unavailable: {e}") from e

    t0 = time.time()
    browser = None
    context = None
    try:
        p = sync_playwright().__enter__()
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if cookie:
            context.set_extra_http_headers({"Cookie": cookie})
        page = context.new_page()
        page.goto(
            url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000)
        )

        selectors = [
            f'div[data-aid="{answer_id}"] div.RichContent-inner',
            f'div[data-aid="{answer_id}"] div.RichContent',
            "div.RichContent-inner",
            "div.RichContent",
            "article",
        ]
        text = ""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(timeout=int(timeout_seconds * 1000))
                text = loc.inner_text().strip()
                if text:
                    break
            except Exception:
                continue

        title = None
        try:
            title = page.locator("h1.QuestionHeader-title").first.inner_text().strip()
        except Exception:
            title = None
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()

    if not text:
        raise RuntimeError("failed to extract answer text")

    rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", text)
    return {
        "question_id": question_id,
        "answer_id": answer_id,
        "question_title": title,
        "answer_text_path": rel,
        "source_url": url,
        "fetched_at": utc_now_iso(),
        "duration_ms": int((time.time() - t0) * 1000),
        "dry_run": False,
    }


def _post_answer_draft(ctx: ActionContext, params: dict[str, Any]) -> Any:
    content_md = params.get("content_md")
    if content_md is None:
        raw_input = params.get("input", None)
        if raw_input is None:
            raw_input = ctx.input
        if isinstance(raw_input, dict) and "summary_path" in raw_input:
            content_md = read_text(ctx, str(raw_input["summary_path"]))
        elif isinstance(raw_input, str):
            content_md = raw_input
        else:
            content_md = ""

    content_md = str(content_md)
    if not content_md.strip():
        raise ValueError("content_md is empty")

    question_url = str(params.get("question_url", "")).strip()
    if not question_url:
        question_url = str(params.get("url", "")).strip()
    if not question_url:
        raise ValueError("question_url is required")

    rel = write_text(ctx, "zhihu/post_content.md", content_md)

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {"attempted": False, "saved_path": rel, "dry_run": True}

    cookie = _get_cookie(params)
    if not cookie:
        return {
            "attempted": False,
            "saved_path": rel,
            "dry_run": False,
            "error": "missing ZHIHU_COOKIE",
        }

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {
            "attempted": False,
            "saved_path": rel,
            "dry_run": False,
            "error": f"playwright unavailable: {e}",
        }

    timeout_seconds = float(params.get("timeout_seconds", 60.0))
    attempted = False
    error: str | None = None
    browser = None
    context = None
    try:
        p = sync_playwright().__enter__()
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.set_extra_http_headers({"Cookie": cookie})
        page = context.new_page()
        page.goto(
            question_url,
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        attempted = True
        try:
            page.keyboard.insert_text(content_md[:5000])
        except Exception:
            pass
    except Exception as e:
        error = str(e)
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()

    return {
        "attempted": attempted,
        "saved_path": rel,
        "dry_run": False,
        "error": error,
    }


class ZhihuDigestPlugin(Plugin):
    """知乎回答总结插件"""

    name = "zhihu-digest"
    version = "0.1.0"
    actions = {
        "zhihu.fetch_answer": _fetch_answer,
        "zhihu.post_answer_draft": _post_answer_draft,
    }
    checks = {}


PLUGIN = ZhihuDigestPlugin
