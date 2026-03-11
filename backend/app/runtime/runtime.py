# @file /backend/app/runtime/runtime.py
# @brief 运行时单例：Registry/RunStore/Runner 初始化
# @create 2026-02-21 00:00:00

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.runtime.builtins import register_builtins
from app.runtime.plugin_loader import load_plugins_into_registry
from app.runtime.registry import Registry
from app.runtime.runner import Runner
from app.runtime.store import RunStore


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    registry = Registry()
    register_builtins(registry)
    load_plugins_into_registry(registry)
    return registry


@lru_cache(maxsize=1)
def get_store() -> RunStore:
    artifacts_dir = Path(__file__).resolve().parents[2] / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return RunStore(artifacts_dir=artifacts_dir)


@lru_cache(maxsize=1)
def get_runner() -> Runner:
    return Runner(registry=get_registry(), store=get_store())

