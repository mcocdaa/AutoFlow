# @file /backend/app/core/plugin_manager.py
# @brief 插件管理器 - 负责插件注册和加载（基于 Hook 模式）
# @create 2026-03-27

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core import hook_manager, setting_manager
from app.core.registry import registry


class PluginManager:
    """插件管理器

    职责：
    1. 扫描并注册插件
    2. 加载插件后端代码
    3. 通过 hook 让插件注册 actions/checks
    """

    @hook_manager.wrap_hooks(
        "plugin_manager_construct_before", "plugin_manager_construct_after"
    )
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.plugins_dir: Optional[Path] = None
        self.plugins: Dict[str, Any] = {}
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self._initialized = False

    @hook_manager.wrap_hooks(after="plugin_manager_register_arguments")
    def register_arguments(self, parser: argparse.ArgumentParser):
        """注册 argparse 参数

        Args:
            parser: argparse.ArgumentParser 实例
        """
        pass

    @hook_manager.wrap_hooks("plugin_manager_init_before", "plugin_manager_init_after")
    def init(self, args: argparse.Namespace):
        """初始化插件管理器

        Args:
            args: 解析后的参数
        """
        if self._initialized:
            return

        self.plugins_dir = Path(setting_manager.get("PLUGINS_DIR", ""))
        self.plugins = self._load_registry()
        self.logger.info(f"[PluginManager] 发现 {len(self.plugins)} 个插件:")
        for key, info in self.plugins.items():
            self.logger.info(f"  - {key} ({info['type']})")

        self.register_hooks()
        self._run_plugin_registration_hook()
        self._initialized = True

    def _run_plugin_registration_hook(self):
        """运行插件注册钩子 - 让插件注册 actions/checks 和节点元数据"""
        self.logger.info("[PluginManager] 触发插件注册钩子: registry_register")
        hook_manager.run_sync("registry_register", registry)

        # 让插件注册自定义节点元数据（图标、颜色、端口等）
        from app.core.node_registry import node_registry
        self.logger.info("[PluginManager] 触发节点元数据注册钩子: node_meta_register")
        hook_manager.run_sync("node_meta_register", node_registry)

    def register_hooks(self):
        """注册插件钩子 - 直接从文件路径动态导入插件"""
        if not self.plugins_dir:
            self.logger.warning("插件目录未设置，跳过插件注册")
            return

        if str(self.plugins_dir.parent) not in sys.path:
            sys.path.insert(0, str(self.plugins_dir.parent))

        for key, info in self.plugins.items():
            try:
                plugin_path = Path(info["path"])
                if not plugin_path.is_absolute():
                    plugin_path = (self.plugins_dir / plugin_path).resolve()

                module_file = None
                if plugin_path.is_file() and plugin_path.suffix == ".py":
                    module_file = plugin_path
                elif plugin_path.is_dir():
                    init_file = plugin_path / "__init__.py"
                    if init_file.exists():
                        module_file = init_file
                    else:
                        self.logger.warning(
                            f"插件目录 {plugin_path} 下未找到 __init__.py，跳过"
                        )
                        continue
                else:
                    self.logger.warning(f"插件路径无效: {plugin_path}，跳过")
                    continue

                module_name = f"plugins.{key.replace(os.sep, '.').replace('/', '.')}"
                self.logger.debug(f"正在从文件加载插件: {module_file}")

                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec is None or spec.loader is None:
                    self.logger.error(f"无法为插件创建模块规范: {key}")
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                self.loaded_plugins[key] = self.plugins[key]
                self.plugin_modules[key] = module
                self.logger.info(f"成功加载插件: {info['name']} ({key})")

            except Exception as e:
                self.logger.error(f"导入插件 {key} 失败: {e}", exc_info=True)
                module_name = f"plugins.{key.replace(os.sep, '.').replace('/', '.')}"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                if key in self.loaded_plugins:
                    del self.loaded_plugins[key]

    def _load_registry(self) -> Dict[str, Any]:
        """加载插件注册表（简化版，不要求 plugin.yaml）

        Returns:
            {plugin_key: {enabled, path, name, type, manifest}}
        """
        if not self.plugins_dir or not self.plugins_dir.exists():
            self.logger.warning("插件目录不存在或未设置，跳过加载插件注册表")
            return {}

        registry_path = self.plugins_dir / "plugins.yaml"

        if not registry_path.exists():
            self.logger.debug(f"插件注册表文件不存在: {registry_path}")
            return {}

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"读取插件注册表失败: {e}", exc_info=True)
            return {}

        plugins = {}
        for key, cfg in data.get("plugins", {}).items():
            if cfg is None:
                continue
            if not cfg.get("enabled", True):
                self.logger.debug(f"插件 {key} 已禁用，跳过")
                continue

            try:
                if "path" in cfg:
                    path = Path(cfg["path"])
                    if not path.is_absolute():
                        path = (self.plugins_dir / path).resolve()
                    else:
                        path = path.resolve()
                else:
                    path = (self.plugins_dir / key).resolve()

                if not path.exists():
                    self.logger.warning(f"插件路径不存在: {path}，跳过插件 {key}")
                    continue

                if path.is_dir():
                    init_file = path / "__init__.py"
                    if not init_file.exists():
                        self.logger.warning(
                            f"插件目录 {path} 下未找到 __init__.py，跳过插件 {key}"
                        )
                        continue
                    manifest = {"name": key, "type": "unknown"}
                elif path.suffix == ".py":
                    manifest = {
                        "name": path.stem,
                        "type": "unknown",
                        "backend_entry": path.name,
                    }
                else:
                    self.logger.warning(
                        f"插件路径既不是目录也不是 .py 文件: {path}，跳过插件 {key}"
                    )
                    continue

                plugin_type = manifest.get("type", "unknown")

                plugins[key] = {
                    "enabled": True,
                    "path": str(path),
                    "name": manifest.get(
                        "name", key.split("/")[-1] if "/" in key else key
                    ),
                    "type": plugin_type,
                    "manifest": manifest,
                }
                self.logger.debug(f"成功加载插件注册表项: {key} ({path})")

            except Exception as e:
                self.logger.error(f"处理插件 {key} 时发生错误: {e}", exc_info=True)
                continue

        return plugins

    def get_plugin_secrets(self) -> List[Dict[str, Any]]:
        """从已注册插件中提取密钥定义

        Returns:
            密钥定义列表
        """
        secrets = []
        for key, info in self.plugins.items():
            manifest = info.get("manifest", {})
            for secret in manifest.get("secrets", []):
                secrets.append(
                    {
                        "name": secret["name"],
                        "description": secret.get("description", ""),
                        "level": secret.get("level", "optional"),
                        "default": secret.get("default", None),
                        "source": info["name"],
                    }
                )
        return secrets

    def get_all(self) -> List[Dict]:
        """获取所有已加载插件的信息"""
        return list(self.loaded_plugins.values())


plugin_manager = PluginManager()
