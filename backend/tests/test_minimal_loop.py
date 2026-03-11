# @file /backend/tests/test_minimal_loop.py
# @brief 最小闭环测试：dummy 插件 + API 执行 flow
# @create 2026-02-21 00:00:00

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_plugins_contains_dummy_echo() -> None:
    client = _client()
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "dummy.echo" in data["actions"]


def test_execute_flow_with_dummy_echo() -> None:
    flow_yaml = """
version: "1"
name: "demo"
steps:
  - id: "s1"
    action:
      type: "dummy.echo"
      params:
        message: "hi"
    check:
      type: "text.contains"
      params:
        needle: "hi"
""".lstrip()

    client = _client()
    resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "input": {"foo": "bar"}})
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "success"
    assert run["flow_name"] == "demo"
    assert len(run["steps"]) == 1
    assert run["steps"][0]["status"] == "success"
    assert run["steps"][0]["check_passed"] is True
    assert run["steps"][0]["action_output"]["message"] == "hi"
    assert run["steps"][0]["action_output"]["input"] == {"foo": "bar"}

    run_id = run["run_id"]
    resp2 = client.get(f"/api/v1/runs/{run_id}")
    assert resp2.status_code == 200
    run2 = resp2.json()
    assert run2["run_id"] == run_id
