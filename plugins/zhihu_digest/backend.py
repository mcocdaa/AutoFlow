# @file /plugins/zhihu_digest/backend.py
# @brief 知乎回答总结插件后端实现
# @create 2026-03-15 00:00:00

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.plugin.registry import ActionContext


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return _is_truthy(os.getenv("AUTOFLOW_ZHIHU_DRY_RUN"))


def _parse_answer_url(url: str) -> tuple[str | None, str | None]:
    m = re.search(r"/question/(\d+)/answer/(\d+)", url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_text(ctx: ActionContext, rel_path: str, text: str) -> str:
    out_path = ctx.artifacts_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return rel_path


def _read_text(ctx: ActionContext, path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        return p.read_text(encoding="utf-8")

    candidate = (ctx.artifacts_dir / p).resolve()
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")

    return (_repo_root() / p).resolve().read_text(encoding="utf-8")


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


class ZhihuDigestPlugin:
    def __init__(self) -> None:
        self.name = "zhihu-digest"
        self.version = "0.1.0"
        self.actions = {
            "zhihu.fetch_answer": self.fetch_answer,
            "zhihu.post_answer_draft": self.post_answer_draft,
        }

    def fetch_answer(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        url = str(params.get("url", "")).strip()
        if not url:
            raise ValueError("url is required")

        question_id, answer_id = _parse_answer_url(url)
        if question_id is None or answer_id is None:
            raise ValueError("unsupported zhihu answer url")

        if _dry_run(ctx, params):
            answer_text = "点赞后弹出来的\"已赞同\"可以上下拖动。"
            rel = _write_text(ctx, f"zhihu/answers/{answer_id}.txt", answer_text)
            return {
                "question_id": question_id,
                "answer_id": answer_id,
                "question_title": None,
                "answer_text_path": rel,
                "source_url": url,
                "fetched_at": _utc_now_iso(),
                "dry_run": True,
            }

        mode = str(params.get("mode", "auto")).lower()
        timeout_seconds = float(params.get("timeout_seconds", 30))
        cookie = _get_cookie(params)

        if mode in {"auto", "playwright"}:
            return self._fetch_answer_playwright(
                ctx=ctx,
                url=url,
                question_id=question_id,
                answer_id=answer_id,
                timeout_seconds=timeout_seconds,
                cookie=cookie,
            )
        raise ValueError(f"unsupported mode: {mode}")

    def _fetch_answer_playwright(
        self,
        *,
        ctx: ActionContext,
        url: str,
        question_id: str,
        answer_id: str,
        timeout_seconds: float,
        cookie: str | None,
    ) -> Any:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(f"playwright unavailable: {e}") from e

        t0 = time.time()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            if cookie:
                context.set_extra_http_headers({"Cookie": cookie})
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))

            selectors = [
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

            context.close()
            browser.close()

        if not text:
            raise RuntimeError("failed to extract answer text")

        rel = _write_text(ctx, f"zhihu/answers/{answer_id}.txt", text)
        return {
            "question_id": question_id,
            "answer_id": answer_id,
            "question_title": title,
            "answer_text_path": rel,
            "source_url": url,
            "fetched_at": _utc_now_iso(),
            "duration_ms": int((time.time() - t0) * 1000),
            "dry_run": False,
        }

    def post_answer_draft(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        content_md = params.get("content_md")
        if content_md is None:
            raw_input = params.get("input", None)
            if raw_input is None:
                raw_input = ctx.input
            if isinstance(raw_input, dict) and "summary_path" in raw_input:
                content_md = _read_text(ctx, str(raw_input["summary_path"]))
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

        rel = _write_text(ctx, "zhihu/post_content.md", content_md)

        if _dry_run(ctx, params):
            return {"attempted": False, "saved_path": rel, "dry_run": True}

        cookie = _get_cookie(params)
        if not cookie:
            return {"attempted": False, "saved_path": rel, "dry_run": False, "error": "missing ZHIHU_COOKIE"}

        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            return {"attempted": False, "saved_path": rel, "dry_run": False, "error": f"playwright unavailable: {e}"}

        timeout_seconds = float(params.get("timeout_seconds", 60.0))
        attempted = False
        error: str | None = None
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                context.set_extra_http_headers({"Cookie": cookie})
                page = context.new_page()
                page.goto(question_url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
                attempted = True
                try:
                    page.keyboard.insert_text(content_md[:5000])
                except Exception:
                    pass
                context.close()
                browser.close()
            except Exception as e:
                error = str(e)

        return {"attempted": attempted, "saved_path": rel, "dry_run": False, "error": error}


def register() -> ZhihuDigestPlugin:
    return ZhihuDigestPlugin()
