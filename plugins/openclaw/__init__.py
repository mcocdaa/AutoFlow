# @file /plugins/openclaw/__init__.py
# @brief OpenClaw 插件：集成 HTTP 请求、Shell 命令执行、KnowFlow 记录
# @create 2026-03-14

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.runtime.registry import ActionContext, CheckContext


class OpenClawPlugin:
    """OpenClaw 插件：提供 HTTP 请求、Shell 命令执行、KnowFlow 记录等能力"""

    def __init__(self) -> None:
        self.name = "openclaw"
        self.version = "0.1.0"
        self.actions = {
            "openclaw.http_request": self.http_request,
            "openclaw.exec": self.exec_command,
            "openclaw.knowflow_record": self.knowflow_record,
        }
        self.checks = {
            "openclaw.status_code_ok": self.status_code_ok,
            "openclaw.exit_code_zero": self.exit_code_zero,
        }

    # ==================== Actions ====================

    def http_request(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        """
        通用 HTTP 请求
        params:
            - method: GET/POST/PUT/DELETE
            - url: 请求 URL
            - headers: 可选，请求头 dict
            - body: 可选，请求体
            - timeout: 可选，默认 30 秒
        """
        method = params.get("method", "GET").upper()
        url = params.get("url")
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout", 30)

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
                # 尝试解析 JSON
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
            }
        except URLError as e:
            return {
                "status_code": None,
                "headers": None,
                "body": None,
                "error": str(e.reason),
            }
        except Exception as e:
            return {
                "status_code": None,
                "headers": None,
                "body": None,
                "error": str(e),
            }

    def exec_command(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        """
        执行 shell 命令
        params:
            - command: 要执行的命令
            - cwd: 可选，工作目录
            - timeout: 可选，默认 60 秒
        """
        command = params.get("command")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 60)

        if not command:
            return {"exit_code": None, "stdout": "", "stderr": "command is required", "error": "command is required"}

        try:
            result = subprocess.run(
                command,
                shell=True,
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
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "error": str(e),
            }

    def knowflow_record(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        """
        调用 KnowFlow 记录知识项
        params:
            - base_url: 可选，默认 http://localhost:3000
            - name: 知识项名称
            - project_id: 项目 ID
            - archive_type: 可选，默认 document
            - summary: 摘要
            - content: 内容
            - agent_source: 可选，来源 agent ID
        """
        base_url = params.get("base_url", "http://localhost:3000")
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
            # Step 1: 创建知识项
            create_url = f"{base_url}/api/v1/item"
            payload = {
                "name": name,
                "projectId": project_id,
                "archiveType": archive_type,
                "summary": summary,
                "content": content,
            }

            # 添加 agent_source 字段（如果 KnowFlow 支持）
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

            # Step 2: 更新 OpenClaw 来源标记
            update_url = f"{base_url}/api/v1/plugins/knowflow_openclaw/items/{item_id}/openclaw"
            update_payload = {"agent": agent_source, "source": "autoflow"}
            update_data = json.dumps(update_payload).encode("utf-8")

            update_req = Request(update_url, data=update_data, method="PUT")
            update_req.add_header("Content-Type", "application/json")

            try:
                with urlopen(update_req, timeout=30) as response:
                    response.read()  # 确认更新成功
            except HTTPError:
                # 更新失败不影响整体成功
                pass

            return {"item_id": item_id, "name": name, "success": True}

        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {"item_id": None, "name": name, "success": False, "error": f"HTTP {e.code}: {error_body}"}
        except URLError as e:
            return {"item_id": None, "name": name, "success": False, "error": str(e.reason)}
        except Exception as e:
            return {"item_id": None, "name": name, "success": False, "error": str(e)}

    # ==================== Checks ====================

    def status_code_ok(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        """
        检查 HTTP 状态码是否符合预期
        params:
            - expected: 期望的状态码，默认 200
        """
        expected = params.get("expected", 200)
        action_output = ctx.action_output

        if not action_output:
            return False

        status_code = action_output.get("status_code")
        return status_code == expected

    def exit_code_zero(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        """
        检查命令退出码是否为 0
        """
        action_output = ctx.action_output

        if not action_output:
            return False

        exit_code = action_output.get("exit_code")
        return exit_code == 0


def register() -> OpenClawPlugin:
    return OpenClawPlugin()