# @file /backend/tests/test_plugin_loader.py
# @brief Tests for plugin_loader: YAML parsing, config loading, module path
# @create 2026-08-10

from __future__ import annotations

import sys
from pathlib import Path

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
    """Integration tests for load_plugins with temp plugin directories."""

    def test_loads_directory_plugin_with_config(self, tmp_path: Path, monkeypatch):
        """Create a temp plugin directory with hooks.py and config.yaml."""
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "test_plugin"

        # Create plugin structure
        plugin_dir.mkdir(parents=True)
        # __init__.py re-exports register (standard plugin convention)
        (plugin_dir / "__init__.py").write_text(
            "from plugins.test_plugin.hooks import register\n"
        )
        (plugin_dir / "hooks.py").write_text(
            "def register(registry, config=None):\n"
            "    registry.register_plugin(name='test', version='1.0')\n"
            "    if config:\n"
            '        name = config.get("defaults", {}).get("name", "fallback")\n'
            "        registry.register_plugin(name=name, version='1.0')\n"
        )
        _write_yaml(
            plugin_dir / "config.yaml",
            {"defaults": {"name": "from_config"}},
        )
        _write_yaml(
            plugins_dir / "plugins.yaml",
            {"plugins": {"test_plugin": {"enabled": True, "path": "test_plugin"}}},
        )

        # Make plugins dir importable
        parent_dir = str(plugins_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        monkeypatch.setattr(
            "app.runtime.plugin_loader.DEFAULT_PLUGINS_DIR", plugins_dir
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir", lambda: plugins_dir
        )

        load_plugins(registry)

        plugins = registry.list_plugins()
        names = [p.name for p in plugins]
        assert "test" in names
        assert "from_config" in names

    def test_loads_file_plugin_with_subdir(self, tmp_path: Path, monkeypatch):
        """Test that a .py file in a sub-directory imports correctly."""
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        sub_dir = plugins_dir / "examples"
        sub_dir.mkdir(parents=True)

        # Create a file plugin with hooks.py semantics
        (sub_dir / "hello_world.py").write_text(
            "def register(registry, config=None):\n"
            "    registry.register_plugin(name='hello-from-file', version='1.0')\n"
        )
        _write_yaml(
            plugins_dir / "plugins.yaml",
            {
                "plugins": {
                    "hello": {"enabled": True, "path": "examples/hello_world.py"}
                }
            },
        )

        parent_dir = str(plugins_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        # Add an __init__.py to make "examples" a package
        (sub_dir / "__init__.py").write_text("")

        monkeypatch.setattr(
            "app.runtime.plugin_loader.DEFAULT_PLUGINS_DIR", plugins_dir
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir", lambda: plugins_dir
        )

        load_plugins(registry)

        plugins = registry.list_plugins()
        names = [p.name for p in plugins]
        assert "hello-from-file" in names

    def test_disabled_plugin_not_loaded(self, tmp_path: Path, monkeypatch):
        """Disabled plugins should be skipped entirely."""
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "disabled_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "__init__.py").write_text(
            "from plugins.disabled_plugin.hooks import register\n"
        )
        (plugin_dir / "hooks.py").write_text(
            "def register(registry, config=None):\n"
            "    registry.register_plugin(name='should-not-appear', version='1.0')\n"
        )
        _write_yaml(
            plugins_dir / "plugins.yaml",
            {"plugins": {"disabled_plugin": {"enabled": False}}},
        )

        monkeypatch.setattr(
            "app.runtime.plugin_loader.DEFAULT_PLUGINS_DIR", plugins_dir
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir", lambda: plugins_dir
        )

        load_plugins(registry)

        plugins = registry.list_plugins()
        names = [p.name for p in plugins]
        assert "should-not-appear" not in names
