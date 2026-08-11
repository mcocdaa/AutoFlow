# @file /backend/tests/test_plugin_common.py
# @brief plugins/common 单元测试:Plugin 基类注册行为 + 共享 helpers
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path

from app.core.registry import ActionContext, Registry
from plugins.common.helpers import (
    dry_run_enabled,
    is_truthy,
    read_text,
    safe_name,
    utc_now_iso,
    write_text,
)
from plugins.common.plugin import Plugin


def _ctx(artifacts_dir: Path) -> ActionContext:
    return ActionContext(
        run_id="run-1",
        step_id="step-1",
        input=None,
        vars={},
        artifacts_dir=artifacts_dir,
    )


class TestPluginBase:
    def test_register_registers_plugin_and_actions_checks(self) -> None:
        def _handler(ctx, params):
            return {}

        def _check(ctx, params):
            return True

        class SamplePlugin(Plugin):
            name = "sample"
            version = "2.0.0"
            actions = {"sample.run": _handler}
            checks = {"sample.ok": _check}

        registry = Registry()
        SamplePlugin().register(registry)

        assert [(p.name, p.version) for p in registry.list_plugins()] == [
            ("sample", "2.0.0")
        ]
        assert registry.list_actions() == ["sample.run"]
        assert registry.list_checks() == ["sample.ok"]

    def test_config_defaults_to_empty_dict(self) -> None:
        class SamplePlugin(Plugin):
            name = "sample"
            actions = {}

        p = SamplePlugin()
        assert p.config == {}

        p2 = SamplePlugin(config={"defaults": {"a": 1}})
        assert p2.config["defaults"] == {"a": 1}


class TestIsTruthy:
    def test_bool_values(self) -> None:
        assert is_truthy(True) is True
        assert is_truthy(False) is False

    def test_none_is_false(self) -> None:
        assert is_truthy(None) is False

    def test_string_values(self) -> None:
        assert is_truthy("1") is True
        assert is_truthy(" true ") is True
        assert is_truthy("yes") is True
        assert is_truthy("y") is True
        assert is_truthy("on") is True
        assert is_truthy("0") is False
        assert is_truthy("false") is False
        assert is_truthy("off") is False


class TestDryRunEnabled:
    def test_params_dry_run_wins(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        assert dry_run_enabled(ctx, {"dry_run": True}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_vars_dry_run(self, tmp_path: Path) -> None:
        ctx = ActionContext(
            run_id="r",
            step_id="s",
            input=None,
            vars={"dry_run": True},
            artifacts_dir=tmp_path,
        )
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_env_var(self, tmp_path: Path, monkeypatch) -> None:
        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_default_false(self, tmp_path: Path, monkeypatch) -> None:
        ctx = _ctx(tmp_path)
        monkeypatch.delenv("AUTOFLOW_TEST_DRY_RUN", raising=False)
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is False


class TestReadWriteText:
    def test_write_then_read_roundtrip(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        rel = write_text(ctx, "sub/out.txt", "hello")
        assert rel == "sub/out.txt"
        assert read_text(ctx, "sub/out.txt") == "hello"

    def test_read_absolute_artifacts_path(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        target = tmp_path / "abs.txt"
        target.write_text("abs", encoding="utf-8")
        assert read_text(ctx, str(target)) == "abs"

    def test_read_rejects_path_outside_allowed(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        outside = tmp_path.parent / "outside.txt"
        outside.write_text("nope", encoding="utf-8")
        try:
            read_text(ctx, str(outside))
        except ValueError as e:
            assert "outside allowed directories" in str(e)
        else:
            raise AssertionError("expected ValueError")

    def test_read_extra_roots(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        extra = tmp_path / "extra"
        extra.mkdir()
        target = extra / "data.txt"
        target.write_text("extra-data", encoding="utf-8")
        assert read_text(ctx, str(target), extra_roots=(extra,)) == "extra-data"


class TestUtcNowIso:
    def test_returns_iso_string(self) -> None:
        value = utc_now_iso()
        assert isinstance(value, str)
        assert "+00:00" in value


class TestSafeName:
    def test_strips_directory_and_sanitizes(self) -> None:
        assert safe_name("a/b/c.png", fallback="f.png") == "c.png"
        assert safe_name("c d!.png", fallback="f.png") == "c_d_.png"

    def test_empty_falls_back(self) -> None:
        assert safe_name("", fallback="screenshot.png") == "screenshot.png"
