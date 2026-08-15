# @file /plugins/ai_deepseek/backend.py
# @brief DeepSeek AI 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)
# @update 2026-08-11 迁移为类方法形态,api_key 解析收敛为 self.setting

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from app.core.registry import ActionContext

from plugins.common.helpers import read_text, write_text
from plugins.common.plugin import Plugin


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


class AIDeepSeekPlugin(Plugin):
    """DeepSeek AI 插件"""

    name = "ai-deepseek"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_AI_DRY_RUN"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "ai.deepseek_summarize": self._deepseek_summarize,
        }
        self.checks = {}

    def _get_deepseek_api_key(self, params: dict[str, Any]) -> str:
        """api_key 取值链:params.api_key > defaults.api_key
        > secrets.api_key > DEEPSEEK_API_KEY
        """
        key = self.setting(params, "api_key", env_var="DEEPSEEK_API_KEY")
        if key:
            return key
        raise RuntimeError("missing DEEPSEEK_API_KEY")

    def _deepseek_summarize(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
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

        if self.is_dry_run(ctx, params):
            summary = "（dry_run）示例总结：要点已整理。"
            out_rel = write_text(ctx, "ai/summary.md", summary)
            return {
                "summary_path": out_rel,
                "prompt_path": prompt_rel,
                "dry_run": True,
                "provider": "deepseek",
            }

        api_key = self._get_deepseek_api_key(params)
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


PLUGIN = AIDeepSeekPlugin
