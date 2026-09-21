# @file /backend/tests/test_new_features.py
# @brief 新特性单元测试: Secrets 保密柜与脱敏、Cron 调度、Webhook 外部网关、扩展 MCP 工具、Flow Hub
# @create 2026-09-20

import hashlib
import hmac
import json
from pathlib import Path

import pytest
from app.core.secrets_vault import SecretsVault
from app.runtime.cron.scheduler import (
    predict_next_runs,
    validate_cron_expression,
)
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


# ---------------- 1. Secrets 保密柜与脱敏 ----------------


def test_secrets_vault_encryption_and_masking(tmp_path: Path):
    vault_dir = tmp_path / "vault"
    vault = SecretsVault(vault_dir, master_key="super-secret-master-key-12345")

    # 1. 设置凭据
    vault.set_secret("OPENAI_KEY", "sk-1234567890abcdefghijklmnopqrstuvwxyz")
    vault.set_secret("DB_PASSWORD", "SuperSecretPass999")

    # 2. 获取凭据
    assert vault.get_secret("OPENAI_KEY") == "sk-1234567890abcdefghijklmnopqrstuvwxyz"
    assert vault.get_secret("DB_PASSWORD") == "SuperSecretPass999"

    # 3. 列出脱敏凭据
    listed = vault.list_secrets()
    assert len(listed) == 2
    key_map = {item["key"]: item["masked_value"] for item in listed}
    assert "sk****yz" in key_map["OPENAI_KEY"]
    assert "Su****99" in key_map["DB_PASSWORD"]

    # 4. 文本脱敏测试
    raw_log = "Sending request with auth Bearer sk-1234567890abcdefghijklmnopqrstuvwxyz and DB_PASSWORD=SuperSecretPass999"
    masked_log = vault.mask_text(raw_log)
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in masked_log
    assert "SuperSecretPass999" not in masked_log

    # 5. 持久化重载测试
    vault2 = SecretsVault(vault_dir, master_key="super-secret-master-key-12345")
    assert vault2.get_secret("OPENAI_KEY") == "sk-1234567890abcdefghijklmnopqrstuvwxyz"


def test_secrets_api(client: TestClient):
    # 写入凭据
    res = client.post(
        "/api/v1/secrets", json={"key": "TEST_KEY", "value": "my-secret-val-123"}
    )
    assert res.status_code == 200

    # 查询凭据
    res = client.get("/api/v1/secrets")
    assert res.status_code == 200
    data = res.json()
    assert any(item["key"] == "TEST_KEY" for item in data)

    # 删除凭据
    res = client.delete("/api/v1/secrets/TEST_KEY")
    assert res.status_code == 200


# ---------------- 2. Cron 调度引擎 ----------------


def test_cron_validation_and_prediction():
    assert validate_cron_expression("*/5 * * * *") is True
    assert validate_cron_expression("0 0 * * *") is True
    assert validate_cron_expression("invalid_cron") is False

    next_runs = predict_next_runs("*/15 * * * *", count=3)
    assert len(next_runs) == 3
    assert all("T" in dt for dt in next_runs)


def test_cron_api(client: TestClient):
    # 验证与预测 API
    res = client.post(
        "/api/v1/cron/validate", json={"expression": "*/10 * * * *", "count": 4}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert len(data["next_runs"]) == 4

    # 非法表达式
    res = client.post("/api/v1/cron/validate", json={"expression": "abc def"})
    assert res.status_code == 200
    assert res.json()["valid"] is False

    # 查询任务列表
    res = client.get("/api/v1/cron/jobs")
    assert res.status_code == 200


# ---------------- 3. Webhook 外部网关 ----------------


def test_webhook_trigger_with_hmac(client: TestClient):
    # example flow 位于 flows/example.flow.yaml
    flow_name = "example"
    secret_token = "test-webhook-secret"

    payload = json.dumps({"test_param": "hello_from_webhook"}).encode("utf-8")
    signature = hmac.new(
        secret_token.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    # 1. 签名正确，同步执行 (wait=true)
    res = client.post(
        f"/api/v1/webhooks/{flow_name}/{secret_token}?wait=true",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["flow_name"] == "example"
    assert data["status"] == "success"

    # 2. 签名错误
    res = client.post(
        f"/api/v1/webhooks/{flow_name}/{secret_token}",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalid_signature_hex",
        },
    )
    assert res.status_code == 401


# ---------------- 4. Flow Hub 市场 ----------------


def test_flow_hub_api(client: TestClient):
    # 列表查询
    res = client.get("/api/v1/hub/flows")
    assert res.status_code == 200
    flows = res.json()
    assert len(flows) >= 3

    # 详情查询
    first_id = flows[0]["id"]
    res = client.get(f"/api/v1/hub/flows/{first_id}")
    assert res.status_code == 200
    assert "yaml" in res.json()


# ---------------- 5. MCP 新增工具测试 ----------------


def test_mcp_new_tools():
    from app.main import app

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    with TestClient(app) as client:
        # 1. tools/list 包含新增工具
        tools_res = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers=headers,
        )
        assert tools_res.status_code == 200
        tools = tools_res.json()["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        assert "get_flow" in tool_names
        assert "validate_flow" in tool_names
        assert "time_travel_run" in tool_names
        assert "get_run_diff" in tool_names
        assert "search_flow_hub" in tool_names

        # 2. validate_flow
        valid_yaml = """version: "1"
name: test_valid
steps:
  - id: s1
    action:
      type: dummy.echo
      params: {message: "hi"}
"""
        res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "validate_flow",
                    "arguments": {"flow_yaml": valid_yaml},
                },
            },
            headers=headers,
        )
        assert res.status_code == 200
        assert "valid" in res.json()["result"]["content"][0]["text"]

        # 3. search_flow_hub
        res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "search_flow_hub", "arguments": {"query": "SRE"}},
            },
            headers=headers,
        )
        assert res.status_code == 200
        assert "sre" in res.json()["result"]["content"][0]["text"].lower()
