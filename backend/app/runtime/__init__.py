# @file /backend/app/runtime/__init__.py
# @brief 运行时核心模块 - Registry/Runner/Store 单例初始化（基于 Hook 模式）
# @create 2026-03-15
# @update 2026-03-27 重构为基于 Hook 的插件系统

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.registry import registry
from app.runtime.actions import register_builtins
from app.runtime.runner import Runner
from app.runtime.storage import RunStore


@lru_cache(maxsize=1)
def get_registry():
    """获取全局 registry（已通过 hook 注册了所有插件）"""
    register_builtins(registry)
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
