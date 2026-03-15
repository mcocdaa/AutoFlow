# @file /plugins/desktop_checkin/tests/test_desktop_checkin_plugin.py
# @brief 桌面自动打卡插件最小闭环测试（dry_run）
# @create 2026-02-22 00:00:00

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_desktop_checkin_actions_listed() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "desktop.type_text" in data["actions"]
    assert "desktop.screenshot" in data["actions"]


def test_desktop_checkin_dry_run_does_not_leak_secret_and_writes_artifact() -> None:
    flow_yaml = """
version: "1"
name: "desktop-checkin-dry-run"
steps:
  - id: "type"
    action:
      type: "desktop.type_text"
      params:
        text: "secret123"
        secret: true
  - id: "shot"
    action:
      type: "desktop.screenshot"
      params:
        name: "dry.png"
""".lstrip()

    client = TestClient(app)
    resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"dry_run": True}})
    assert resp.status_code == 200
    run = resp.json()

    dumped = json.dumps(run, ensure_ascii=False)
    assert "secret123" not in dumped

    assert run["status"] == "success"
    assert len(run["steps"]) == 2
    assert run["steps"][0]["action_output"]["secret"] is True
    assert "text" not in run["steps"][0]["action_output"]

    rel = run["steps"][1]["action_output"]["path"]
    artifacts_dir = Path(__file__).resolve().parents[2] / "backend" / "artifacts" / run["run_id"]
    assert (artifacts_dir / rel).exists()
