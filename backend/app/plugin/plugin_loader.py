# @file /backend/app/plugin/plugin_loader.py
# @brief 从仓库 plugins 目录加载插件并注册 Action/Check
# @create 2026-02-21 00:00:00
# @update 2026-03-15 支持新插件格式（backend.py + plugin.yaml + config.yaml）

from __future__ import annotations

import importlib.util
import os
import sys
import yaml
from pathlib import Path
from types import ModuleType
from typing import Any

from .registry import ActionContext, Registry


class PluginLoadError(RuntimeError):
    pass


def _repo_root() -> Path:
    container_plugins = Path("/app/plugins")
    if container_plugins.exists():
        return container_plugins.parent
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


def _load_plugin_config(plugin_dir: Path) -> dict[str, Any]:
    config = {"meta": {}, "defaults": {}, "secrets": []}

    plugin_yaml = plugin_dir / "plugin.yaml"
    if plugin_yaml.exists():
        try:
            config["meta"] = yaml.safe_load(plugin_yaml.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    config_yaml = plugin_dir / "config.yaml"
    if config_yaml.exists():
        try:
            data = yaml.safe_load(config_yaml.read_text(encoding="utf-8")) or {}
            config["defaults"] = data.get("defaults", {})
            config["secrets"] = data.get("secrets", {})
        except Exception:
            pass

    return config


def _is_plugin_enabled(meta: dict[str, Any]) -> bool:
    return meta.get("enabled", True)


def _load_plugin_entry_file(plugin_dir: Path, plugin_id: str) -> Path | None:
    backend_py = plugin_dir / "backend.py"
    if backend_py.exists():
        return backend_py

    init_py = plugin_dir / "__init__.py"
    if init_py.exists():
        return init_py

    return None


def load_plugins_into_registry(registry: Registry, *, plugins_dir: Path | None = None) -> None:
    from app.core.config import settings
    root_dirs: list[Path] = []
    if plugins_dir is not None:
        root_dirs.append(plugins_dir)
    else:
        root_dirs.append(_repo_root() / "plugins")
        extra = settings.AUTOFLOW_PLUGIN_DIRS
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

            plugin_id = child.name.replace("-", "_")

            plugin_config = _load_plugin_config(child)
            meta = plugin_config.get("meta", {})

            if not _is_plugin_enabled(meta):
                continue

            entry_file = _load_plugin_entry_file(child, plugin_id)
            if entry_file is None:
                continue

            try:
                module = _load_module_from_file(f"autoflow_plugins.{plugin_id}", entry_file, package_dir=child)
                register = getattr(module, "register", None)
                if register is None or not callable(register):
                    continue
                try:
                    plugin_obj = register(config=plugin_config)
                except TypeError:
                    plugin_obj = register()  # 兼容不接受 config 的旧插件
                _register_plugin_object(registry, plugin_id, plugin_obj)
            except Exception as e:
                registry.add_plugin_error(plugin_id=plugin_id, file_path=str(entry_file), error=str(e))
