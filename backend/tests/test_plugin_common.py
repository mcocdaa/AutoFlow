# @file /backend/tests/test_plugin_common.py
# @brief plugins/common 单元测试:Plugin 基类注册行为 + 共享 helpers
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path

from app.core.registry import ActionContext, Registry
from plugins.common.helpers import (
    is_truthy,
    read_text,
    resolve_env_value,
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

            def __init__(self, config=None):
                super().__init__(config)
                self.actions = {"sample.run": self._run}
                self.checks = {"sample.ok": self._ok}

            def _run(self, ctx, params):
                return _handler(ctx, params)

            def _ok(self, ctx, params):
                return _check(ctx, params)

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

        p = SamplePlugin()
        assert p.config == {}
        assert p.defaults == {}
        assert p.secrets == {}

        p2 = SamplePlugin(config={"defaults": {"a": 1}, "secrets": {"b": "x"}})
        assert p2.defaults == {"a": 1}
        assert p2.secrets == {"b": "x"}


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


class TestIsDryRun:
    def test_params_dry_run_wins(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        assert P().is_dry_run(ctx, {"dry_run": True}) is True

    def test_vars_dry_run(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = ActionContext(
            run_id="r",
            step_id="s",
            input=None,
            vars={"dry_run": True},
            artifacts_dir=tmp_path,
        )
        assert P().is_dry_run(ctx, {}) is True

    def test_env_var(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert P().is_dry_run(ctx, {}) is True

    def test_params_override_env(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert P().is_dry_run(ctx, {"dry_run": False}) is False

    def test_default_false(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.delenv("AUTOFLOW_TEST_DRY_RUN", raising=False)
        assert P().is_dry_run(ctx, {}) is False

    def test_no_dry_run_env_class_attr(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"

        ctx = _ctx(tmp_path)
        assert P().is_dry_run(ctx, {}) is False

    def test_params_false_overrides_vars_true(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = ActionContext(
            run_id="r",
            step_id="s",
            input=None,
            vars={"dry_run": True},
            artifacts_dir=tmp_path,
        )
        assert P().is_dry_run(ctx, {"dry_run": False}) is False


class TestSetting:
    def test_params_priority(self, tmp_path: Path) -> None:
        p = Plugin(config={"defaults": {"k": "d"}, "secrets": {"k": "s"}})
        assert p.setting({"k": "p"}, "k") == "p"

    def test_defaults_then_secrets(self, tmp_path: Path) -> None:
        p = Plugin(config={"defaults": {"k": "d"}, "secrets": {"k": "s"}})
        assert p.setting({}, "k") == "d"
        p2 = Plugin(config={"secrets": {"k": "s"}})
        assert p2.setting({}, "k") == "s"

    def test_env_var_fallback(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({}, "k", env_var="TEST_K") == "env-value"

    def test_env_var_only_when_explicit(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({}, "k") is None

    def test_default_returned_when_missing(self, tmp_path: Path) -> None:
        assert Plugin().setting({}, "k", default="fallback") == "fallback"

    def test_empty_string_falls_through(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({"k": "  "}, "k", env_var="TEST_K") == "env-value"

    def test_env_prefix_resolution(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("REAL_KEY", "secret-123")
        assert Plugin().setting({"k": "env:REAL_KEY"}, "k") == "secret-123"

    def test_false_is_not_skipped(self, tmp_path: Path) -> None:
        assert Plugin().setting({"k": False}, "k", default="d") is False

    def test_secrets_empty_string_falls_through(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        p = Plugin(config={"secrets": {"k": "  "}})
        assert p.setting({}, "k", env_var="TEST_K") == "env-value"

    def test_env_missing_prefix_returns_none(self, tmp_path: Path) -> None:
        # params 层显式写 env:MISSING:解析失败返回 None,不再向低层回退
        assert Plugin().setting({"k": "env:MISSING"}, "k", default="d") is None


class TestErrorResult:
    def test_basic(self) -> None:
        r = Plugin().error_result("boom")
        assert r == {"error": "boom", "error_type": "unknown_error"}

    def test_explicit_type_and_fields(self) -> None:
        r = Plugin().error_result(
            "nope", error_type="http_error", status_code=500, body=None
        )
        assert r == {
            "error": "nope",
            "error_type": "http_error",
            "status_code": 500,
            "body": None,
        }


class TestResolveEnvValue:
    def test_env_prefix(self, monkeypatch) -> None:
        monkeypatch.setenv("A", "1")
        assert resolve_env_value("env:A") == "1"

    def test_env_prefix_unset_returns_none(self) -> None:
        assert resolve_env_value("env:NOT_SET_ANYWHERE") is None

    def test_plain_value_passthrough(self) -> None:
        assert resolve_env_value("plain") == "plain"
        assert resolve_env_value(42) == 42


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
