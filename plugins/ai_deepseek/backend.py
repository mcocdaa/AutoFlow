# @file /plugins/ai_deepseek/backend.py
# @brief DeepSeek AI 插件后端实现
# @create 2026-03-15 00:00:00

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.plugin.registry import ActionContext


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_text(ctx: ActionContext, path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        return p.read_text(encoding="utf-8")
    candidate = (ctx.artifacts_dir / p).resolve()
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return (_repo_root() / p).resolve().read_text(encoding="utf-8")


def _write_text(ctx: ActionContext, rel_path: str, text: str) -> str:
    out_path = ctx.artifacts_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return rel_path


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
    return _is_truthy(os.getenv("AUTOFLOW_AI_DRY_RUN"))


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
    def __init__(self, *, base_url: str = "https://api.deepseek.com", timeout_seconds: float = 60.0) -> None:
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


class AIDeepSeekPlugin:
    def __init__(self) -> None:
        self.name = "ai-deepseek"
        self.version = "0.1.0"
        self.actions = {
            "ai.deepseek_summarize": self.deepseek_summarize,
        }

    def deepseek_summarize(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        model = str(params.get("model", "deepseek-chat"))
        system_prompt = params.get("system_prompt")
        temperature = params.get("temperature")
        max_tokens = params.get("max_tokens")

        raw_input = params.get("input", None)
        if raw_input is None:
            raw_input = ctx.input

        if isinstance(raw_input, dict) and "answer_text_path" in raw_input:
            input_text = _read_text(ctx, str(raw_input["answer_text_path"]))
        elif isinstance(raw_input, dict) and "path" in raw_input:
            input_text = _read_text(ctx, str(raw_input["path"]))
        elif isinstance(raw_input, str):
            input_text = raw_input
        elif raw_input is None:
            input_text = ""
        else:
            input_text = str(raw_input)

        if not input_text.strip():
            raise ValueError("input is empty")

        prompt_rel = _write_text(ctx, "ai/prompt.txt", input_text)

        if _dry_run(ctx, params):
            summary = "（dry_run）示例总结：要点已整理。"
            out_rel = _write_text(ctx, "ai/summary.md", summary)
            return {"summary_path": out_rel, "prompt_path": prompt_rel, "dry_run": True, "provider": "deepseek"}

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

        out_rel = _write_text(ctx, "ai/summary.md", result.content)
        return {"summary_path": out_rel, "prompt_path": prompt_rel, "model": model, "dry_run": False, "provider": "deepseek"}


def register() -> AIDeepSeekPlugin:
    return AIDeepSeekPlugin()
