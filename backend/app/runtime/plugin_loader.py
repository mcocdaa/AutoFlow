# @file /backend/app/runtime/plugin_loader.py
# @brief 插件加载器 - 读取 plugins.yaml 启用的插件并注册到 Registry
# @create 2026-08-08
# @update 2026-08-10 阶段二:收敛为 PLUGIN (Plugin 子类) 协议最终形态
# @update 2026-08-11 注释同步类方法 ABI

from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from app.core.registry import Registry
from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)

DEFAULT_PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"


def _plugins_dir() -> Path:
    configured = setting_manager.get("PLUGINS_DIR", "")
    if configured:
        return Path(configured)
    return DEFAULT_PLUGINS_DIR


def _load_registry_entries(plugins_dir: Path) -> dict[str, dict[str, Any]]:
    """读取 plugins.yaml,返回 {plugin_key: {path}} 启用的插件条目"""
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


def _load_plugin_config(plugin_dir: Path) -> dict[str, Any] | None:
    """加载插件目录下 config.yaml 并解析 secrets(环境变量值)

    无 config.yaml 时返回 None;secrets 块逐项按环境变量解析。
    """
    config_path = plugin_dir / "config.yaml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load plugin config {config_path}: {e}")
        return None

    secrets = config.get("secrets")
    if isinstance(secrets, dict):
        resolved: dict[str, str | None] = {}
        for key, env_var in secrets.items():
            if isinstance(env_var, str):
                resolved[key] = os.getenv(env_var)
        config["secrets"] = resolved

    return config


def load_plugins(registry: Registry) -> None:
    """加载 plugins.yaml 中启用的插件,识别 PLUGIN (Plugin 子类) 完成注册

    插件模块需暴露 PLUGIN = XxxPlugin (Plugin 子类),见 plugins/common/plugin.py。
    handlers 为实例方法,由插件 __init__ 绑定到 self.actions/self.checks。
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

    # 延迟导入:依赖上面 sys.path 注入仓库根目录后 plugins 包才可导入
    from plugins.common.plugin import Plugin

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

            # 模块名取解析后路径的目录名/文件名,与 plugins.yaml 的 key 解耦;
            # 文件插件取相对 plugins_dir 的路径(去 .py 后缀、分隔符转点号),
            # 例如 plugins/examples/hello_world.py → plugins.examples.hello_world
            if path.is_dir():
                module_name = path.name
            else:
                rel = path.resolve().relative_to(plugins_dir.resolve())
                module_name = (
                    str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
                )
            module = importlib.import_module(f"plugins.{module_name}")

            plugin_cls = getattr(module, "PLUGIN", None)
            if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, Plugin)):
                raise AttributeError(
                    f"插件模块 {module_name} 未暴露 PLUGIN (Plugin 子类)"
                )

            # config.yaml 仅对目录插件加载,文件插件传入 None
            config = None
            if path.is_dir():
                config = _load_plugin_config(path)

            plugin = plugin_cls(config)
            plugin.register(registry)
            logger.info(f"成功加载插件: {key} ({path})")
        except Exception as e:
            logger.error(f"加载插件 {key} 失败: {e}", exc_info=True)
            registry.add_plugin_error(plugin_id=key, file_path=str(path), error=str(e))
