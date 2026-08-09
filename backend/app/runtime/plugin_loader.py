# @file /backend/app/runtime/plugin_loader.py
# @brief 插件加载器 - runtime 统一加载 plugins.yaml 启用的插件并注册到 Registry
# @create 2026-08-08

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from app.core.registry import Registry
from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)

DEFAULT_PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


def _plugins_dir() -> Path:
    configured = setting_manager.get("PLUGINS_DIR", "")
    if configured:
        return Path(configured)
    return DEFAULT_PLUGINS_DIR


def _load_registry_entries(plugins_dir: Path) -> dict[str, dict[str, Any]]:
    """读取 plugins.yaml,返回 {plugin_key: {path, enabled}}"""
    registry_path = plugins_dir / "plugins.yaml"
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"读取插件注册表失败: {registry_path} - {e}")
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for key, cfg in data.get("plugins", {}).items():
        if cfg is None:
            continue
        if not cfg.get("enabled", True):
            logger.debug(f"插件 {key} 已禁用,跳过")
            continue

        raw_path = cfg.get("path", key)
        path = Path(raw_path)
        if not path.is_absolute():
            path = (plugins_dir / path).resolve()

        entries[key] = {"path": path}
    return entries


def load_plugins(registry: Registry) -> None:
    """加载 plugins.yaml 中启用的插件,调用其 register(registry) 完成注册

    插件模块需暴露 register(registry) 函数(见 plugins/*/hooks.py)。
    单个插件加载失败不会影响其他插件,错误会记录到 registry。
    """
    plugins_dir = _plugins_dir()
    if not plugins_dir.exists():
        logger.warning(f"插件目录不存在: {plugins_dir},跳过插件加载")
        return

    entries = _load_registry_entries(plugins_dir)
    if not entries:
        logger.debug("插件注册表为空,跳过插件加载")
        return

    parent_dir = str(plugins_dir.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    for key, entry in entries.items():
        path: Path = entry["path"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"插件路径不存在: {path}")

            if path.is_dir():
                if not (path / "__init__.py").exists():
                    raise FileNotFoundError(f"插件目录 {path} 下未找到 __init__.py")
            elif not path.is_file() or path.suffix != ".py":
                raise ValueError(f"插件路径既不是目录也不是 .py 文件: {path}")

            module_name = f"plugins.{key}"
            module = importlib.import_module(module_name)

            register_fn = getattr(module, "register", None)
            if not callable(register_fn):
                raise AttributeError(
                    f"插件模块 {module_name} 未暴露 register(registry)"
                )

            register_fn(registry)
            logger.info(f"成功加载插件: {key} ({path})")
        except Exception as e:
            logger.error(f"加载插件 {key} 失败: {e}", exc_info=True)
            registry.add_plugin_error(plugin_id=key, file_path=str(path), error=str(e))
