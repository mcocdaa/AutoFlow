# @file /backend/tests/test_mcp_server.py
# @brief 测试 MCP Server 挂载:握手、工具调用、token 鉴权、MCP_ENABLED 开关
# @create 2026-09-18

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.registry import Registry
from app.mcp.server import MCP_PATH, create_mcp_binding, install_mcp
from app.runtime.runner import Runner
from app.runtime.storage.store import RunStore
from fastapi import FastAPI
from fastapi.testclient import TestClient

INLINE_FLOW = """\
version: "1"
name: mcp-server-demo
steps:
  - id: s1
    action:
      type: test.echo
      params:
        message: hi
"""

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}

INIT_PAYLOAD = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "0"},
    },
}


def _echo_action(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {"message": params.get("message", "ok")}


def _build_client(tmp_path: Path, *, token: str = "") -> TestClient:
    registry = Registry()
    registry.register_action("test.echo", _echo_action)
    store = RunStore(artifacts_dir=tmp_path / "artifacts")
    binding = create_mcp_binding(
        registry,
        store,
        Runner(registry, store),
        flows_dir=tmp_path / "flows",
        token=token,
        version="test",
    )
    app = FastAPI(lifespan=binding.lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    install_mcp(app, binding)
    return TestClient(app)


def _call_tool(client: TestClient, name: str, arguments: dict[str, Any]) -> dict:
    response = client.post(
        MCP_PATH,
        json={
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    return response.json()["result"]


def test_initialize_and_tool_listing(tmp_path: Path) -> None:
    with _build_client(tmp_path) as client:
        response = client.post(MCP_PATH, json=INIT_PAYLOAD, headers=HEADERS)

        assert response.status_code == 200
        info = response.json()["result"]["serverInfo"]
        assert info["name"] == "AutoFlow"

        tools = client.post(
            MCP_PATH,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=HEADERS,
        ).json()["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert {
            "list_capabilities",
            "list_flows",
            "run_flow",
            "get_run",
            "list_runs",
            "replay_run",
            "get_artifact",
        } <= names


def test_run_flow_tool_returns_run_result(tmp_path: Path) -> None:
    with _build_client(tmp_path) as client:
        result = _call_tool(
            client, "run_flow", {"flow_yaml": INLINE_FLOW, "wait": True}
        )

        assert result["isError"] is False
        payload = json.loads(result["content"][0]["text"])
        assert payload["flow_name"] == "mcp-server-demo"
        assert payload["status"] == "success"


def test_token_required_when_configured(tmp_path: Path) -> None:
    with _build_client(tmp_path, token="s3cret") as client:
        missing = client.post(MCP_PATH, json=INIT_PAYLOAD, headers=HEADERS)
        wrong = client.post(
            MCP_PATH,
            json=INIT_PAYLOAD,
            headers={**HEADERS, "Authorization": "Bearer nope"},
        )
        ok = client.post(
            MCP_PATH,
            json=INIT_PAYLOAD,
            headers={**HEADERS, "Authorization": "Bearer s3cret"},
        )
        health = client.get("/health")

        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert missing.headers["www-authenticate"] == "Bearer"
        assert ok.status_code == 200
        assert health.status_code == 200


def test_mcp_disabled_by_env(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        f"r = TestClient(app).post('{MCP_PATH}', json={{'jsonrpc': '2.0', 'id': 1, "
        "'method': 'initialize', 'params': {}}, "
        "headers={'Accept': 'application/json, text/event-stream'})\n"
        "print(r.status_code)\n"
    )
    env = {
        **os.environ,
        "MCP_ENABLED": "0",
        "PYTHONPATH": str(repo_root / "backend"),
    }
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )

    assert completed.stdout.strip() == "404"
