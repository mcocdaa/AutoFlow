# @file /plugins/openclaw/tests/test_openclaw_plugin.py
# @brief OpenClaw 插件单元测试
# @create 2026-03-14

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.plugin.registry import ActionContext, CheckContext, Registry

import sys as _sys, os as _os
_plugins_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '../../..'))
if _plugins_root not in _sys.path:
    _sys.path.insert(0, _plugins_root)
from plugins.openclaw.backend import OpenClawPlugin, register


try:
    from plugins.openclaw import register
    PLUGIN_AVAILABLE = True
except ImportError:
    PLUGIN_AVAILABLE = False


class TestOpenClawHTTPRequestAction:
    """测试 openclaw.http_request action"""

    @pytest.fixture
    def plugin(self):
        if not PLUGIN_AVAILABLE:
            pytest.skip("OpenClaw plugin not installed")
        return register()

    @pytest.fixture
    def mock_httpx(self):
        with patch("plugins.openclaw.httpx") as mock_httpx:
            yield mock_httpx

    def test_http_request_success(self, plugin, mock_httpx):
        """正常 HTTP 请求返回 status_code/headers/body"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"message": "ok"}'
        mock_httpx.Client.return_value.__enter__.return_value.request.return_value = mock_response

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {
            "method": "GET",
            "url": "http://example.com/api",
            "headers": {"Accept": "application/json"},
            "timeout": 30
        }

        result = plugin.actions["openclaw.http_request"](ctx, params)

        mock_httpx.Client.assert_called_once()
        mock_client = mock_httpx.Client.return_value.__enter__.return_value
        mock_client.request.assert_called_once_with(
            method="GET",
            url="http://example.com/api",
            headers={"Accept": "application/json"},
            timeout=30
        )

        assert result == {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"message": "ok"}'
        }

    def test_http_request_with_json_body(self, plugin, mock_httpx):
        """POST 请求带 JSON body"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = ""
        mock_httpx.Client.return_value.__enter__.return_value.request.return_value = mock_response

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {
            "method": "POST",
            "url": "http://example.com/api",
            "json": {"key": "value"}
        }

        result = plugin.actions["openclaw.http_request"](ctx, params)

        mock_client = mock_httpx.Client.return_value.__enter__.return_value
        mock_client.request.assert_called_once_with(
            method="POST",
            url="http://example.com/api",
            json={"key": "value"}
        )
        assert result["status_code"] == 201

    def test_http_request_exception(self, plugin, mock_httpx):
        """HTTP 请求异常时抛出 RuntimeError"""
        mock_httpx.Client.return_value.__enter__.return_value.request.side_effect = Exception("Network error")

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {
            "method": "GET",
            "url": "http://example.com"
        }

        with pytest.raises(RuntimeError, match="HTTP request failed"):
            plugin.actions["openclaw.http_request"](ctx, params)


class TestOpenClawExecAction:
    """测试 openclaw.exec action"""

    @pytest.fixture
    def plugin(self):
        if not PLUGIN_AVAILABLE:
            pytest.skip("OpenClaw plugin not installed")
        return register()

    @pytest.fixture
    def mock_subprocess(self):
        with patch("plugins.openclaw.backend.subprocess") as mock_subprocess:
            yield mock_subprocess

    def test_exec_success(self, plugin, mock_subprocess):
        """执行命令成功返回 exit_code/stdout/stderr"""
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = b"hello\n"
        mock_process.stderr = b""
        mock_subprocess.run.return_value = mock_process

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {
            "command": "echo hello",
            "shell": True,
            "cwd": "/tmp"
        }

        result = plugin.actions["openclaw.exec"](ctx, params)

        mock_subprocess.run.assert_called_once_with(
            "echo hello",
            shell=True,
            cwd="/tmp",
            capture_output=True,
            text=False
        )

        assert result == {
            "exit_code": 0,
            "stdout": "hello\n",
            "stderr": "",
            "success": True
        }

    def test_exec_failure(self, plugin, mock_subprocess):
        """命令失败时 exit_code != 0"""
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stdout = b""
        mock_process.stderr = b"error"
        mock_subprocess.run.return_value = mock_process

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {"command": "false"}

        result = plugin.actions["openclaw.exec"](ctx, params)

        assert result["exit_code"] == 1
        assert result["success"] is False
        assert result["stderr"] == "error"

    def test_exec_timeout(self, plugin, mock_subprocess):
        """命令超时"""
        mock_subprocess.run.side_effect = TimeoutError("Command timed out")

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {"command": "sleep 10", "timeout": 1}

        with pytest.raises(RuntimeError, match="Command execution failed"):
            plugin.actions["openclaw.exec"](ctx, params)


class TestOpenClawKnowflowRecordAction:
    """测试 openclaw.knowflow_record action"""

    @pytest.fixture
    def plugin(self):
        if not PLUGIN_AVAILABLE:
            pytest.skip("OpenClaw plugin not installed")
        return register()

    @pytest.fixture
    def mock_knowflow_record(self):
        with patch("plugins.openclaw.knowflow_record") as mock_knowflow:
            yield mock_knowflow

    def test_knowflow_record_success(self, plugin, mock_knowflow_record):
        """成功创建 KnowFlow 记录"""
        mock_knowflow_record.return_value = {"id": "123", "name": "test item"}

        ctx = ActionContext(
            run_id="test-run",
            step_id="step1",
            input=None,
            vars={},
            artifacts_dir=Path("/tmp/artifacts")
        )
        params = {
            "name": "Test Record",
            "projectId": "test-project",
            "type": "document",
            "summary": "Test summary",
            "content": "Test content",
            "agent": "qa_ops"
        }

        result = plugin.actions["openclaw.knowflow_record"](ctx, params)

        mock_knowflow_record.assert_called_once_with(
            name="Test Record",
            projectId="test-project",
            type="document",
            summary="Test summary",
            content="Test content",
            agent="qa_ops",
            foldLevel=3
        )

        assert result == {"id": "123", "name": "test item"}


class TestStatusCodeOkCheck:
    """测试 openclaw.status_code_ok check"""

    @pytest.fixture
    def plugin(self):
        if not PLUGIN_AVAILABLE:
            pytest.skip("OpenClaw plugin not installed")
        return register()

    def test_status_code_ok_true(self, plugin):
        """status_code=200 返回 True"""
        check_func = plugin.checks["openclaw.status_code_ok"]
        ctx = CheckContext(
            run_id="test-run",
            step_id="step1",
            action_output={"status_code": 200, "body": "ok"},
            vars={}
        )
        result = check_func(ctx, {})
        assert result is True

    def test_status_code_ok_false(self, plugin):
        """status_code=500 返回 False"""
        check_func = plugin.checks["openclaw.status_code_ok"]
        ctx = CheckContext(
            run_id="test-run",
            step_id="step1",
            action_output={"status_code": 500, "body": "error"},
            vars={}
        )
        result = check_func(ctx, {})
        assert result is False


class TestExitCodeZeroCheck:
    """测试 openclaw.exit_code_zero check"""

    @pytest.fixture
    def plugin(self):
        if not PLUGIN_AVAILABLE:
            pytest.skip("OpenClaw plugin not installed")
        return register()

    def test_exit_code_zero_true(self, plugin):
        """exit_code=0 返回 True"""
        check_func = plugin.checks["openclaw.exit_code_zero"]
        ctx = CheckContext(
            run_id="test-run",
            step_id="step1",
            action_output={"exit_code": 0, "stdout": "ok"},
            vars={}
        )
        result = check_func(ctx, {})
        assert result is True

    def test_exit_code_zero_false(self, plugin):
        """exit_code=1 返回 False"""
        check_func = plugin.checks["openclaw.exit_code_zero"]
        ctx = CheckContext(
            run_id="test-run",
            step_id="step1",
            action_output={"exit_code": 1, "stderr": "error"},
            vars={}
        )
        result = check_func(ctx, {})
        assert result is False




class TestExecSecurity:
    def test_safe_mode_normal_command(self):
        plugin = OpenClawPlugin(config={"defaults": {"safe_mode": True}})
        result = plugin.exec_command(None, {"command": "echo hello"})
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_safe_mode_false_default(self):
        plugin = OpenClawPlugin()
        assert plugin.defaults.get("safe_mode", False) is False
        result = plugin.exec_command(None, {"command": "echo compat"})
        assert result["exit_code"] == 0

    def test_allowed_commands_blocks_disallowed(self):
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo"]}})
        result = plugin.exec_command(None, {"command": "rm -rf /"})
        assert result["exit_code"] == -1
        assert result["error"] == "command_not_allowed"
        assert "not allowed" in result["stderr"]

    def test_allowed_commands_permits_matching(self):
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo"]}})
        result = plugin.exec_command(None, {"command": "echo allowed"})
        assert result["exit_code"] == 0
        assert "allowed" in result["stdout"]

    def test_allowed_commands_empty_no_restriction(self):
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": []}})
        result = plugin.exec_command(None, {"command": "echo unrestricted"})
        assert result["exit_code"] == 0

    def test_args_mode(self):
        plugin = OpenClawPlugin()
        result = plugin.exec_command(None, {"command": "echo", "args": ["from", "args"]})
        assert result["exit_code"] == 0
        assert "from" in result["stdout"]

    def test_config_exec_timeout(self):
        import sys
        plugin = OpenClawPlugin(config={"defaults": {"exec_timeout": 1}})
        if sys.platform == "win32":
            result = plugin.exec_command(None, {"command": "ping -n 5 127.0.0.1"})
        else:
            result = plugin.exec_command(None, {"command": "sleep 5"})
        assert result["exit_code"] == -1
        assert result.get("error") == "timeout"


class TestStructuredErrors:
    def test_http_request_error_has_error_type(self):
        from unittest.mock import patch, MagicMock
        from urllib.error import URLError
        plugin = OpenClawPlugin()
        with patch('plugins.openclaw.backend.urlopen', side_effect=URLError('connection refused')):
            result = plugin.http_request(None, {'method': 'GET', 'url': 'http://fake'})
        assert 'error_type' in result
        assert result['error_type'] == 'network_error'

    def test_exec_timeout_has_error_type(self):
        import subprocess
        from unittest.mock import patch
        plugin = OpenClawPlugin()
        with patch('plugins.openclaw.backend.subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 1)):
            result = plugin.exec_command(None, {'command': 'sleep 99'})
        assert result.get('error_type') == 'timeout'

    def test_knowflow_record_warning_on_update_failure(self):
        from unittest.mock import patch, MagicMock
        from urllib.error import HTTPError
        plugin = OpenClawPlugin()

        create_response = MagicMock()
        create_response.__enter__ = lambda s: s
        create_response.__exit__ = MagicMock(return_value=False)
        create_response.read.return_value = b'{"id": "test-id-123"}'

        def mock_urlopen(req, timeout=30):
            if 'openclaw' in req.full_url:
                raise HTTPError(req.full_url, 404, 'Not Found', {}, None)
            return create_response

        with patch('plugins.openclaw.backend.urlopen', side_effect=mock_urlopen):
            result = plugin.knowflow_record(None, {
                'name': 'test', 'project_id': 'proj1'
            })
        assert result['success'] is True
        assert 'warning' in result
