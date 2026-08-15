# @file /plugins/openclaw/tests/test_openclaw_plugin.py
# @brief openclaw 错误返回与安全控制单测
# @create 2026-08-11

from __future__ import annotations

from unittest.mock import patch

from plugins.openclaw.backend import OpenClawPlugin


def _plugin(config=None) -> OpenClawPlugin:
    return OpenClawPlugin(config)


class _Ctx:
    run_id = "r"
    step_id = "s"
    input = None
    vars = {}
    artifacts_dir = "/tmp"


def test_http_request_missing_url_keeps_literal_dict() -> None:
    # 契约:url is required 分支不含 error_type 键
    result = _plugin()._http_request(_Ctx(), {})
    assert result == {
        "error": "url is required",
        "status_code": None,
        "headers": None,
        "body": None,
    }


def test_exec_command_missing_command() -> None:
    result = _plugin()._exec_command(_Ctx(), {})
    assert result["error"] == "command is required"
    assert result["exit_code"] is None


def test_exec_command_denied_by_whitelist() -> None:
    plugin = _plugin(config={"defaults": {"allowed_commands": [r"^ls$"]}})
    result = plugin._exec_command(_Ctx(), {"command": "rm -rf /"})
    assert result["error"] == "command_not_allowed"
    assert result["exit_code"] == -1


def test_exec_command_timeout_uses_error_result() -> None:
    import subprocess

    def _raise(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    with patch("plugins.openclaw.backend.subprocess.run", side_effect=_raise):
        result = _plugin()._exec_command(_Ctx(), {"command": "sleep 100"})
    assert result["error"] == "timeout"
    assert result["error_type"] == "timeout"
    assert result["exit_code"] == -1
