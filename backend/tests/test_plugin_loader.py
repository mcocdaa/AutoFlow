# @file /backend/tests/test_plugin_loader.py
# @brief Tests for plugin_loader: YAML parsing, config loading, module path
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import yaml
from app.core.registry import Registry
from app.runtime.plugin_loader import (
    _load_plugin_config,
    _load_registry_entries,
    load_plugins,
)


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


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
    """Integration tests for load_plugins with mocked imports."""

    def test_loads_directory_plugin_with_config(self, monkeypatch, tmp_path: Path):
        """Verify load_plugins passes config from config.yaml to register()."""
        registry = Registry()

        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "test_plugin"
        plugin_dir.mkdir(parents=True)

        # __init__.py required for directory plugins
        (plugin_dir / "__init__.py").write_text("")

        # Write a real config.yaml so load_plugins can find it
        _write_yaml(
            plugin_dir / "config.yaml",
            {"defaults": {"name": "from_config"}, "secrets": {}},
        )

        # Create a mock module with a register function
        mock_module = MagicMock()
        mock_register = MagicMock()
        mock_module.register = mock_register

        # Mock out the internals so we don't touch real filesystem
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"test_p": {"path": plugin_dir}},
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            lambda name: mock_module,
        )

        load_plugins(registry)

        # Verify register was called with a config dict containing defaults
        assert mock_register.call_count == 1
        args, _kwargs = mock_register.call_args
        assert args[0] is registry
        config = args[1]
        assert config is not None
        assert config["defaults"] == {"name": "from_config"}

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
        """When config.yaml is missing, register gets config=None."""
        registry = Registry()

        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "test_plugin"
        plugin_dir.mkdir(parents=True)

        # __init__.py required for directory plugins
        (plugin_dir / "__init__.py").write_text("")
        # No config.yaml written

        mock_module = MagicMock()
        mock_register = MagicMock()
        mock_module.register = mock_register

        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"test_p": {"path": plugin_dir}},
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            lambda name: mock_module,
        )

        load_plugins(registry)

        mock_register.assert_called_once_with(registry, None)
