# @file /backend/tests/test_flows_and_catalog.py
# @brief 服务端 /api/v1/flows CRUD、路径穿越防护、MCP Flow 工具与 /api/v1/plugins/catalog 测试
# @create 2026-10-14

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.setting_manager import setting_manager
from app.mcp.tools import get_saved_flow, list_saved_flows, save_flow
from fastapi.testclient import TestClient

SAMPLE_FLOW_YAML = """version: "1"
name: demo_pipeline
description: "Canonical server-side flow"
trigger:
  webhook_enabled: true
  webhook_token: "tok-123"
steps:
  - id: step_1
    name: "Log start"
    action:
      type: core.log
      params:
        message: "hello server flow"
  - id: step_2
    name: "Echo result"
    depends_on:
      - step_1
    action:
      type: dummy.echo
      params:
        message: "done"
"""


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def test_flows_crud_lifecycle(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(setting_manager.config, "FLOWS_DIR", str(flows_dir))

    # 1. 初始列表为空
    res = client.get("/api/v1/flows")
    assert res.status_code == 200
    assert res.json() == []

    # 2. PUT 创建/更新 flow
    put_res = client.put(
        "/api/v1/flows/demo_pipeline",
        json={"slug": "demo_pipeline", "flow_yaml": SAMPLE_FLOW_YAML},
    )
    assert put_res.status_code == 200
    saved = put_res.json()
    assert saved["slug"] == "demo_pipeline"
    assert saved["filename"] == "demo_pipeline.yaml"
    assert saved["name"] == "demo_pipeline"
    assert saved["version"] == "1"
    assert saved["description"] == "Canonical server-side flow"
    assert saved["steps_count"] == 2
    assert saved["webhook_enabled"] is True
    assert saved["flow_yaml"] == SAMPLE_FLOW_YAML
    assert (flows_dir / "demo_pipeline.yaml").is_file()

    # 3. GET 列表包含刚保存的 flow
    list_res = client.get("/api/v1/flows")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["slug"] == "demo_pipeline"

    # 4. GET 单个 flow
    get_res = client.get("/api/v1/flows/demo_pipeline")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "demo_pipeline"
    assert get_res.json()["steps_count"] == 2

    # 5. POST 保存另一个 flow
    post_res = client.post(
        "/api/v1/flows",
        json={"slug": "second_flow", "flow_yaml": SAMPLE_FLOW_YAML},
    )
    assert post_res.status_code == 200
    assert post_res.json()["slug"] == "second_flow"
    assert (flows_dir / "second_flow.yaml").is_file()

    # 6. DELETE 删除 flow
    del_res = client.delete("/api/v1/flows/demo_pipeline")
    assert del_res.status_code == 200
    assert not (flows_dir / "demo_pipeline.yaml").exists()

    # 7. 再次 GET 或 DELETE 已删除的 flow 返回 404
    assert client.get("/api/v1/flows/demo_pipeline").status_code == 404
    assert client.delete("/api/v1/flows/demo_pipeline").status_code == 404


def test_flows_rejects_invalid_yaml_and_path_traversal(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(setting_manager.config, "FLOWS_DIR", str(flows_dir))

    # 1. 非法 YAML 被 400 拒绝
    bad_yaml_res = client.put(
        "/api/v1/flows/bad_flow",
        json={"flow_yaml": "version: '1'\nname: bad\nsteps: not_a_list\n"},
    )
    assert bad_yaml_res.status_code == 400
    assert not (flows_dir / "bad_flow.yaml").exists()

    # 2. 路径穿越与非法 slug 被拒绝
    for malicious_slug in ["..%2Fevil", "foo..bar", "a/b", "bad$slug", ".hidden"]:
        assert client.get(f"/api/v1/flows/{malicious_slug}").status_code == 400
        assert (
            client.put(
                f"/api/v1/flows/{malicious_slug}",
                json={"flow_yaml": SAMPLE_FLOW_YAML},
            ).status_code
            == 400
        )
        assert client.delete(f"/api/v1/flows/{malicious_slug}").status_code == 400

    for dot_slug in ["..", "../evil"]:
        assert client.get(f"/api/v1/flows/{dot_slug}").status_code in (400, 404)
        assert client.put(
            f"/api/v1/flows/{dot_slug}",
            json={"flow_yaml": SAMPLE_FLOW_YAML},
        ).status_code in (400, 404, 405)


def test_mcp_saved_flow_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(setting_manager.config, "FLOWS_DIR", str(flows_dir))

    saved = save_flow(slug="agent_created", flow_yaml=SAMPLE_FLOW_YAML)
    assert saved["slug"] == "agent_created"
    assert (flows_dir / "agent_created.yaml").is_file()

    all_flows = list_saved_flows()
    assert len(all_flows) == 1
    assert all_flows[0]["slug"] == "agent_created"

    fetched = get_saved_flow("agent_created")
    assert fetched["name"] == "demo_pipeline"
    assert fetched["steps_count"] == 2


def test_plugins_catalog_api(client: TestClient) -> None:
    res = client.get("/api/v1/plugins/catalog")
    assert res.status_code == 200
    data = res.json()

    assert "actions" in data
    assert "checks" in data
    assert "catalog" in data
    assert isinstance(data["catalog"], list)
    assert len(data["catalog"]) >= len(data["actions"]) + len(data["checks"])

    by_type = {item["type"]: item for item in data["catalog"]}
    assert "core.log" in by_type
    assert by_type["core.log"]["kind"] == "action"
    assert by_type["core.log"]["label"]
    assert "defaultParams" in by_type["core.log"]

    assert "core.assert_truthy" in by_type
    assert by_type["core.assert_truthy"]["kind"] == "check"
    assert by_type["core.assert_truthy"]["category"] == "check"

    # /api/v1/plugins 同样返回 catalog
    plugins_res = client.get("/api/v1/plugins")
    assert plugins_res.status_code == 200
    assert len(plugins_res.json()["catalog"]) == len(data["catalog"])
