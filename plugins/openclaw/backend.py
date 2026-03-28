# @file /plugins/openclaw/backend.py
# @brief OpenClaw 插件后端实现
# @create 2026-03-15 00:00:00

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.registry import ActionContext, CheckContext


class OpenClawPlugin:
    def __init__(self, config: dict = None) -> None:
        self.name = "openclaw"
        self.version = "0.1.0"
        self.config = config or {}
        self.defaults = self.config.get("defaults", {})
        self.secrets = self.config.get("secrets", {})
        self.actions = {
            "openclaw.http_request": self.http_request,
            "openclaw.exec": self.exec_command,
            "openclaw.knowflow_record": self.knowflow_record,
        }
        self.checks = {
            "openclaw.status_code_ok": self.status_code_ok,
            "openclaw.exit_code_zero": self.exit_code_zero,
        }

    def http_request(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        method = params.get("method", "GET").upper()
        url = params.get("url")
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout") or self.defaults.get("http_timeout", 30)

        if not url:
            return {"error": "url is required", "status_code": None, "headers": None, "body": None}

        try:
            req = Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)

            if body:
                if isinstance(body, (dict, list)):
                    body = json.dumps(body).encode("utf-8")
                    req.add_header("Content-Type", "application/json")
                elif isinstance(body, str):
                    body = body.encode("utf-8")
                req.data = body

            with urlopen(req, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
                try:
                    response_body = json.loads(response_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": response_body,
                }
        except HTTPError as e:
            return {
                "status_code": e.code,
                "headers": dict(e.headers) if e.headers else {},
                "body": e.read().decode("utf-8") if e.fp else None,
                "error": str(e),
                "error_type": "http_error",
            }
        except URLError as e:
            return {
                "status_code": None,
                "headers": None,
                "body": None,
                "error": str(e.reason),
                "error_type": "network_error",
            }
        except Exception as e:
            return {
                "status_code": None,
                "headers": None,
                "body": None,
                "error": str(e),
                "error_type": "unknown_error",
            }

    def exec_command(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        command = params.get("command")
        args = params.get("args")  # 可选参数列表
        cwd = params.get("cwd")
        timeout = params.get("timeout") or self.defaults.get("exec_timeout", 60)
        safe_mode = params.get("safe_mode", self.defaults.get("safe_mode", False))
        allowed_commands = self.defaults.get("allowed_commands", [])

        if not command:
            return {"exit_code": None, "stdout": "", "stderr": "command is required", "error": "command is required"}

        # 白名单校验（若配置了 allowed_commands）
        if allowed_commands:
            matched = any(re.match(pattern, command) for pattern in allowed_commands)
            if not matched:
                return {"exit_code": -1, "stdout": "", "stderr": f"command not allowed: {command}", "error": "command_not_allowed"}

        # 构建执行参数
        # Windows 上内建命令（echo/dir等）需要 shell=True，safe_mode 下仍用 shlex 解析但保留 shell
        _is_windows = sys.platform == "win32"
        if args is not None:
            # 显式传了 args，使用列表模式
            cmd = [command] + list(args)
            use_shell = _is_windows  # Windows 需要 shell=True 才能找到内建命令
        elif safe_mode:
            # safe_mode：用 shlex.split 解析参数，防止注入；Windows 下仍需 shell
            cmd = shlex.split(command, posix=not _is_windows)
            use_shell = _is_windows
        else:
            # 默认：shell=True（向后兼容）
            cmd = command
            use_shell = True

        try:
            result = subprocess.run(
                cmd,
                shell=use_shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "error": "timeout",
                "error_type": "timeout",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "error": str(e),
                "error_type": "unknown_error",
            }

    def knowflow_record(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        default_base_url = (
            self.secrets.get("knowflow_base_url")
            or os.environ.get("KNOWFLOW_BASE_URL")
            or "http://localhost:3000"
        )
        base_url = params.get("base_url") or default_base_url
        name = params.get("name")
        project_id = params.get("project_id")
        archive_type = params.get("archive_type", "document")
        summary = params.get("summary", "")
        content = params.get("content", "")
        agent_source = params.get("agent_source", "autoflow")

        if not name:
            return {"item_id": None, "name": None, "success": False, "error": "name is required"}
        if not project_id:
            return {"item_id": None, "name": name, "success": False, "error": "project_id is required"}

        try:
            create_url = f"{base_url}/api/v1/item"
            payload = {
                "name": name,
                "projectId": project_id,
                "archiveType": archive_type,
                "summary": summary,
                "content": content,
            }

            if agent_source:
                payload["agent"] = agent_source

            data = json.dumps(payload).encode("utf-8")
            req = Request(create_url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")

            with urlopen(req, timeout=30) as response:
                create_result = json.loads(response.read().decode("utf-8"))
                item_id = create_result.get("id") or create_result.get("_id")
                if not item_id:
                    return {"item_id": None, "name": name, "success": False, "error": "Failed to get item_id from response"}

            update_url = f"{base_url}/api/v1/plugins/knowflow_openclaw/items/{item_id}/openclaw"
            update_payload = {"agent": agent_source, "source": "autoflow"}
            update_data = json.dumps(update_payload).encode("utf-8")

            update_req = Request(update_url, data=update_data, method="PUT")
            update_req.add_header("Content-Type", "application/json")

            update_warning = None
            try:
                with urlopen(update_req, timeout=30) as response:
                    response.read()
            except HTTPError as e:
                update_warning = f"openclaw attribute update failed: HTTP {e.code}"
            except Exception as e:
                update_warning = f"openclaw attribute update failed: {e}"

            result = {"item_id": item_id, "name": name, "success": True}
            if update_warning:
                result["warning"] = update_warning
            return result

        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {"item_id": None, "name": name, "success": False, "error": f"HTTP {e.code}: {error_body}", "error_type": "http_error"}
        except URLError as e:
            return {"item_id": None, "name": name, "success": False, "error": str(e.reason), "error_type": "network_error"}
        except Exception as e:
            return {"item_id": None, "name": name, "success": False, "error": str(e), "error_type": "unknown_error"}

    def status_code_ok(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        expected = params.get("expected", 200)
        action_output = ctx.action_output

        if not action_output:
            return False

        status_code = action_output.get("status_code")
        return status_code == expected

    def exit_code_zero(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        action_output = ctx.action_output

        if not action_output:
            return False

        exit_code = action_output.get("exit_code")
        return exit_code == 0


def register(config: dict = None) -> OpenClawPlugin:
    return OpenClawPlugin(config=config)
