# @file /backend/app/core/registry.py
# @brief 全局注册表 - Action/Check 注册表与插件清单（基于 Hook 模式）
# @create 2026-03-27

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ActionContext:
    run_id: str
    step_id: str
    input: Any | None
    vars: dict[str, Any]
    artifacts_dir: Path


@dataclass(frozen=True)
class CheckContext:
    run_id: str
    step_id: str
    action_output: Any | None
    vars: dict[str, Any]


ActionHandler = Callable[[ActionContext, dict[str, Any]], Any]
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]


@dataclass(frozen=True)
class PluginInfo:
    name: str
    version: str


@dataclass(frozen=True)
class PluginLoadErrorInfo:
    plugin_id: str
    file_path: str
    error: str


class Registry:
    """全局注册表

    通过 hook 系统注册 actions 和 checks
    """

    def __init__(self) -> None:
        self._actions: dict[str, ActionHandler] = {}
        self._checks: dict[str, CheckHandler] = {}
        self._plugins: list[PluginInfo] = []
        self._plugin_errors: list[PluginLoadErrorInfo] = []

    def register_plugin(self, name: str, version: str) -> None:
        self._plugins.append(PluginInfo(name=name, version=version))

    def add_plugin_error(self, plugin_id: str, file_path: str, error: str) -> None:
        self._plugin_errors.append(
            PluginLoadErrorInfo(plugin_id=plugin_id, file_path=file_path, error=error)
        )

    def register_action(self, type_name: str, handler: ActionHandler) -> None:
        self._actions[type_name] = handler

    def register_check(self, type_name: str, handler: CheckHandler) -> None:
        self._checks[type_name] = handler

    def get_action(self, type_name: str) -> ActionHandler:
        try:
            return self._actions[type_name]
        except KeyError as e:
            raise KeyError(f"unknown action type: {type_name}") from e

    def get_check(self, type_name: str) -> CheckHandler:
        try:
            return self._checks[type_name]
        except KeyError as e:
            raise KeyError(f"unknown check type: {type_name}") from e

    def list_actions(self) -> list[str]:
        return sorted(self._actions.keys())

    def list_checks(self) -> list[str]:
        return sorted(self._checks.keys())

    def list_plugins(self) -> list[PluginInfo]:
        return list(self._plugins)

    def list_plugin_errors(self) -> list[PluginLoadErrorInfo]:
        return list(self._plugin_errors)

    def clear(self) -> None:
        """清空注册表（用于测试）"""
        self._actions.clear()
        self._checks.clear()
        self._plugins.clear()
        self._plugin_errors.clear()


registry = Registry()
