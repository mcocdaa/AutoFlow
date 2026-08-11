# @file /plugins/ai_deepseek/backend.py
# @brief DeepSeek AI 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
from app.core.registry import ActionContext

from plugins.common.helpers import dry_run_enabled, read_text, write_text
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_AI_DRY_RUN"


def _get_deepseek_api_key(params: dict[str, Any]) -> str:
    key_ref = params.get("api_key")
    if isinstance(key_ref, str) and key_ref.strip():
        if key_ref.startswith("env:"):
            k = os.getenv(key_ref[4:])
            if k:
                return k
        return key_ref
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key
    raise RuntimeError("missing DEEPSEEK_API_KEY")


@dataclass(frozen=True)
class DeepSeekResult:
    content: str
    raw: dict[str, Any]


class DeepSeekClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def chat_completion(
        self,
        *,
        api_key: str,
        input: str,
        system_prompt: str | None = None,
        model: str = "deepseek-chat",
        temperature: float | None = None,
        max_tokens: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> DeepSeekResult:
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{self._base_url}/v1/chat/completions"

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input})

        payload: dict[str, Any] = {"model": model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        client = http_client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"deepseek request failed: {e}") from e
        finally:
            if http_client is None:
                client.close()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"deepseek response parse failed: {e}") from e
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("deepseek returned empty content")
        return DeepSeekResult(content=content, raw=data)


def _deepseek_summarize(ctx: ActionContext, params: dict[str, Any]) -> Any:
    model = str(params.get("model", "deepseek-chat"))
    system_prompt = params.get("system_prompt")
    temperature = params.get("temperature")
    max_tokens = params.get("max_tokens")

    raw_input = params.get("input", None)
    if raw_input is None:
        raw_input = ctx.input

    if isinstance(raw_input, dict) and "answer_text_path" in raw_input:
        input_text = read_text(ctx, str(raw_input["answer_text_path"]))
    elif isinstance(raw_input, dict) and "path" in raw_input:
        input_text = read_text(ctx, str(raw_input["path"]))
    elif isinstance(raw_input, str):
        input_text = raw_input
    elif raw_input is None:
        input_text = ""
    else:
        input_text = str(raw_input)

    if not input_text.strip():
        raise ValueError("input is empty")

    prompt_rel = write_text(ctx, "ai/prompt.txt", input_text)

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        summary = "（dry_run）示例总结：要点已整理。"
        out_rel = write_text(ctx, "ai/summary.md", summary)
        return {
            "summary_path": out_rel,
            "prompt_path": prompt_rel,
            "dry_run": True,
            "provider": "deepseek",
        }

    api_key = _get_deepseek_api_key(params)
    client = DeepSeekClient(
        base_url=str(params.get("base_url", "https://api.deepseek.com")),
        timeout_seconds=float(params.get("timeout_seconds", 60.0)),
    )
    result = client.chat_completion(
        api_key=api_key,
        input=input_text,
        system_prompt=str(system_prompt) if system_prompt is not None else None,
        model=model,
        temperature=float(temperature) if temperature is not None else None,
        max_tokens=int(max_tokens) if max_tokens is not None else None,
    )

    out_rel = write_text(ctx, "ai/summary.md", result.content)
    return {
        "summary_path": out_rel,
        "prompt_path": prompt_rel,
        "model": model,
        "dry_run": False,
        "provider": "deepseek",
    }


class AIDeepSeekPlugin(Plugin):
    """DeepSeek AI 插件"""

    name = "ai-deepseek"
    version = "0.1.0"
    actions = {
        "ai.deepseek_summarize": _deepseek_summarize,
    }
    checks = {}


PLUGIN = AIDeepSeekPlugin
