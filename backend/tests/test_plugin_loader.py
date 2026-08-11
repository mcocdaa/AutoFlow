# @file /backend/tests/test_plugin_loader.py
# @brief Tests for plugin_loader: YAML/config 解析、PLUGIN (Plugin 子类) 加载
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import yaml
from app.core.registry import Registry
from app.runtime.plugin_loader import (
    _load_plugin_config,
    _load_registry_entries,
    load_plugins,
)
from plugins.common.plugin import Plugin


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


class _RecordingPlugin(Plugin):
    """记录构造接收到的 config,便于断言 config 注入。"""

    name = "test-plugin"
    version = "9.9.9"
    actions: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    instances: list[_RecordingPlugin] = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.received_config = config
        _RecordingPlugin.instances.append(self)


class TestLoadRegistryEntries:
    """Test plugins.yaml parsing."""

    def test_empty_when_no_yaml(self, tmp_path: Path):
        entries = _load_registry_entries(tmp_path)
        assert entries == {}

    def test_parses_enabled_plugins(self, tmp_path: Path):
        _write_yaml(
            tmp_path / "plugins.yaml",
            {
                "plugins": {
                    "dummy": {"enabled": True},
                    "disabled_plugin": {"enabled": False},
                }
            },
        )
        entries = _load_registry_entries(tmp_path)
        assert "dummy" in entries
        assert "disabled_plugin" not in entries

    def test_handles_missing_path_key(self, tmp_path: Path):
        _write_yaml(
            tmp_path / "plugins.yaml",
            {"plugins": {"test_plugin": {"enabled": True}}},
        )
        entries = _load_registry_entries(tmp_path)
        assert "test_plugin" in entries
        # Defaults to plugin key as path
        assert entries["test_plugin"]["path"].name == "test_plugin"


class TestLoadPluginConfig:
    """Test config.yaml loading and secrets resolution."""

    def test_none_when_no_config(self, tmp_path: Path):
        config = _load_plugin_config(tmp_path)
        assert config is None

    def test_loads_defaults_and_secrets(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "secret-123")
        monkeypatch.setenv("TEST_BASE_URL", "http://example.com")

        _write_yaml(
            tmp_path / "config.yaml",
            {
                "defaults": {"timeout": 30, "dry_run": False},
                "secrets": {
                    "api_key": "TEST_API_KEY",
                    "base_url": "TEST_BASE_URL",
                    "missing": "MISSING_VAR",
                },
            },
        )
        config = _load_plugin_config(tmp_path)
        assert config is not None
        assert config["defaults"] == {"timeout": 30, "dry_run": False}
        assert config["secrets"] == {
            "api_key": "secret-123",
            "base_url": "http://example.com",
            "missing": None,
        }

    def test_no_secrets_block(self, tmp_path: Path):
        _write_yaml(tmp_path / "config.yaml", {"defaults": {"x": 1}})
        config = _load_plugin_config(tmp_path)
        assert config is not None
        assert config["defaults"] == {"x": 1}
        assert "secrets" not in config


class TestPluginLoaderIntegration:
    """Integration tests for load_plugins with mocked imports (PLUGIN 协议)。"""

    def _make_plugin_dir(self, tmp_path: Path) -> Path:
        plugin_dir = tmp_path / "plugins" / "test_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
        return plugin_dir

    def _mock_import(self, monkeypatch, plugins_dir: Path, module) -> None:
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"test_p": {"path": plugins_dir / "test_plugin"}},
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            lambda name: module,
        )

    def test_loads_directory_plugin_with_config(self, monkeypatch, tmp_path: Path):
        """PLUGIN 识别 + config.yaml 解析结果注入构造 + 注册到 registry。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        plugin_dir = self._make_plugin_dir(tmp_path)

        _write_yaml(
            plugin_dir / "config.yaml",
            {"defaults": {"name": "from_config"}, "secrets": {}},
        )

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        assert len(_RecordingPlugin.instances) == 1
        config = _RecordingPlugin.instances[0].received_config
        assert config is not None
        assert config["defaults"] == {"name": "from_config"}

        plugins = registry.list_plugins()
        assert [(p.name, p.version) for p in plugins] == [("test-plugin", "9.9.9")]

    def test_disabled_plugin_not_loaded(self, monkeypatch):
        """Disabled plugins should not trigger module loading."""
        registry = Registry()

        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: Path("/fake/plugins"),
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {},
        )

        import_mock = MagicMock()
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            import_mock,
        )

        load_plugins(registry)

        # import_module should never be called for empty entries
        import_mock.assert_not_called()

    def test_loads_plugin_passes_none_config_when_missing(
        self, monkeypatch, tmp_path: Path
    ):
        """缺少 config.yaml 时 PLUGIN 构造应收到 config=None。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        self._make_plugin_dir(tmp_path)

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        assert len(_RecordingPlugin.instances) == 1
        assert _RecordingPlugin.instances[0].received_config is None

    def test_module_without_plugin_reports_error(self, monkeypatch, tmp_path: Path):
        """模块未暴露 PLUGIN 时应上报到 registry.add_plugin_error。"""
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        self._make_plugin_dir(tmp_path)

        # spec=[] 使任意属性访问抛 AttributeError,模拟无 PLUGIN 的模块
        mock_module = MagicMock(spec=[])

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        errors = registry.list_plugin_errors()
        assert len(errors) == 1
        assert "PLUGIN" in errors[0].error
        assert errors[0].plugin_id == "test_p"

    def test_loads_file_plugin_with_subdirectory_module_name(
        self, monkeypatch, tmp_path: Path
    ):
        """文件插件:模块名解析为相对路径点号形式(目录/文件形态保留),config 为 None。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        file_plugin = plugins_dir / "examples" / "hello_world.py"
        file_plugin.parent.mkdir(parents=True)
        file_plugin.write_text("", encoding="utf-8")

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"hello": {"path": file_plugin}},
        )
        imported_names: list[str] = []

        def _fake_import(name: str):
            imported_names.append(name)
            return mock_module

        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            _fake_import,
        )

        load_plugins(registry)

        assert imported_names == ["plugins.examples.hello_world"]
        assert len(_RecordingPlugin.instances) == 1
        assert _RecordingPlugin.instances[0].received_config is None
        assert [(p.name, p.version) for p in registry.list_plugins()] == [
            ("test-plugin", "9.9.9")
        ]
