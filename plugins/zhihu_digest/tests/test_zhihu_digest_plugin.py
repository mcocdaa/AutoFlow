# @file /plugins/zhihu_digest/tests/test_zhihu_digest_plugin.py
# @brief 知乎回答总结插件最小闭环测试（dry_run）
# @create 2026-02-22 00:00:00

from __future__ import annotations

from pathlib import Path

from app.main import app
from fastapi.testclient import TestClient


def test_zhihu_digest_actions_listed() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "zhihu.fetch_answer" in data["actions"]
    assert "ai.deepseek_summarize" in data["actions"]


def test_zhihu_digest_dry_run_writes_artifacts() -> None:
    flow_yaml = """
version: "1"
name: "zhihu-digest-dry-run"
steps:
  - id: "fetch"
    action:
      type: "zhihu.fetch_answer"
      params:
        url: "https://www.zhihu.com/question/784489052/answer/1946200783080125276"
  - id: "sum"
    action:
      type: "ai.deepseek_summarize"
      params:
        system_prompt: "总结要点"
""".lstrip()

    client = TestClient(app)
    resp = client.post(
        "/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"dry_run": True}}
    )
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "success"

    fetch = run["steps"][0]["action_output"]
    summ = run["steps"][1]["action_output"]
    assert fetch["dry_run"] is True
    assert summ["dry_run"] is True

    artifacts_dir = (
        Path(__file__).resolve().parents[2] / "backend" / "artifacts" / run["run_id"]
    )
    assert (artifacts_dir / fetch["answer_text_path"]).exists()
    assert (artifacts_dir / summ["prompt_path"]).exists()
    assert (artifacts_dir / summ["summary_path"]).exists()
