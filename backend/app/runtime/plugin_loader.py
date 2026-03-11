# @file /backend/app/runtime/plugin_loader.py
# @brief 从仓库 plugins 目录加载插件并注册 Action/Check
# @create 2026-02-21 00:00:00

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from app.runtime.registry import ActionContext, Registry


class PluginLoadError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_module_from_file(module_name: str, file_path: Path, *, package_dir: Path | None = None) -> ModuleType:
    submodule_search_locations = [str(package_dir)] if package_dir is not None else None
    spec = importlib.util.spec_from_file_location(module_name, file_path, submodule_search_locations=submodule_search_locations)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"unable to load spec: {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_plugin_id(file_path: Path) -> str:
    return file_path.stem.replace("-", "_")


def _register_plugin_object(registry: Registry, plugin_id: str, plugin_obj: Any) -> None:
    name = getattr(plugin_obj, "name", plugin_id)
    version = getattr(plugin_obj, "version", "0.0.0")
    registry.register_plugin(name=str(name), version=str(version))

    actions = getattr(plugin_obj, "actions", None)
    if isinstance(actions, dict) and actions:
        for type_name, handler in actions.items():
            if callable(handler):
                registry.register_action(str(type_name), handler)
        checks = getattr(plugin_obj, "checks", None)
        if isinstance(checks, dict) and checks:
            for type_name, handler in checks.items():
                if callable(handler):
                    registry.register_check(str(type_name), handler)
        return

    execute = getattr(plugin_obj, "execute", None)
    if callable(execute):
        action_type = f"{plugin_id}.execute"

        def _execute_action(ctx: ActionContext, params: dict[str, Any], _execute: Any = execute) -> Any:
            return _execute(**params)

        registry.register_action(action_type, _execute_action)


def load_plugins_into_registry(registry: Registry, *, plugins_dir: Path | None = None) -> None:
    root_dirs: list[Path] = []
    if plugins_dir is not None:
        root_dirs.append(plugins_dir)
    else:
        root_dirs.append(_repo_root() / "plugins")
        extra = os.getenv("AUTOFLOW_PLUGIN_DIRS", "")
        for raw in [p.strip() for p in extra.split(os.pathsep) if p.strip()]:
            root_dirs.append(Path(raw))

    for root_dir in root_dirs:
        if not root_dir.exists():
            continue

        examples_dir = root_dir / "examples"
        if examples_dir.exists():
            for file_path in sorted(examples_dir.glob("*.py")):
                if file_path.name.startswith("_"):
                    continue
                plugin_id = _normalize_plugin_id(file_path)
                try:
                    module = _load_module_from_file(f"autoflow_plugins.examples.{plugin_id}", file_path)
                    register = getattr(module, "register", None)
                    if register is None or not callable(register):
                        continue
                    _register_plugin_object(registry, plugin_id, register())
                except Exception as e:
                    registry.add_plugin_error(plugin_id=plugin_id, file_path=str(file_path), error=str(e))

        for child in sorted(root_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name in {"examples", "__pycache__"}:
                continue
            init_py = child / "__init__.py"
            if not init_py.exists():
                continue
            plugin_id = child.name.replace("-", "_")
            try:
                module = _load_module_from_file(f"autoflow_plugins.{plugin_id}", init_py, package_dir=child)
                register = getattr(module, "register", None)
                if register is None or not callable(register):
                    continue
                _register_plugin_object(registry, plugin_id, register())
            except Exception as e:
                registry.add_plugin_error(plugin_id=plugin_id, file_path=str(init_py), error=str(e))
