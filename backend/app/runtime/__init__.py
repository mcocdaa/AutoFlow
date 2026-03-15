# @file /backend/app/runtime/__init__.py
# @brief 运行时核心模块 - Registry/Runner/Store 单例初始化
# @create 2026-03-15
# @update 2026-03-15 合并 runtime/core 到 runtime 根目录

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.runtime.actions import register_builtins
from app.plugin.plugin_loader import load_plugins_into_registry
from app.plugin.registry import Registry
from app.runtime.runner import Runner
from app.runtime.storage import RunStore


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    registry = Registry()
    register_builtins(registry)
    load_plugins_into_registry(registry)
    return registry


@lru_cache(maxsize=1)
def get_store() -> RunStore:
    artifacts_dir = Path(__file__).resolve().parents[1] / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return RunStore(artifacts_dir=artifacts_dir)


@lru_cache(maxsize=1)
def get_runner() -> Runner:
    return Runner(registry=get_registry(), store=get_store())


__all__ = ["get_registry", "get_store", "get_runner"]
