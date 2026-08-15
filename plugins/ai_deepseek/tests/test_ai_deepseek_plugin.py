# @file /plugins/ai_deepseek/tests/test_ai_deepseek_plugin.py
# @brief ai_deepseek api_key 取值链单测
# @create 2026-08-11

from __future__ import annotations

import pytest
from plugins.ai_deepseek.backend import AIDeepSeekPlugin


def _plugin(config=None) -> AIDeepSeekPlugin:
    return AIDeepSeekPlugin(config)


def test_api_key_from_params() -> None:
    assert _plugin()._get_deepseek_api_key({"api_key": "k-123"}) == "k-123"


def test_api_key_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("MY_KEY", "k-env")
    assert _plugin()._get_deepseek_api_key({"api_key": "env:MY_KEY"}) == "k-env"


def test_api_key_from_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k-secret")
    assert (
        _plugin(config={"secrets": {"api_key": "k-secret"}})._get_deepseek_api_key({})
        == "k-secret"
    )


def test_api_key_missing_raises(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="missing DEEPSEEK_API_KEY"):
        _plugin()._get_deepseek_api_key({})
