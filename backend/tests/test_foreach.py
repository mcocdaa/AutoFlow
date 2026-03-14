# @file /backend/tests/test_foreach.py
# @brief 测试 forEach 循环功能
# @create 2026-03-14

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_foreach_basic() -> None:
    """测试遍历列表 ["a","b","c"]，每次 echo {{vars.item}}"""
    flow_yaml = """
version: "1"
name: "foreach_test"
steps:
  - id: "loop"
    action:
      type: "dummy.echo"
      params:
        message: "{{vars.item}}"
    for_each: "{{vars.items}}"
    for_item_var: "item"
""".lstrip()

    client = _client()
    resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"items": ["a", "b", "c"]}})
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "success"
    assert len(run["steps"]) == 1
    
    step = run["steps"][0]
    assert step["status"] == "success"
    # 验证 iterations 记录
    assert step["iterations"] is not None
    assert len(step["iterations"]) == 3
    
    # 验证每次迭代的输出
    assert step["iterations"][0]["item"] == "a"
    assert step["iterations"][0]["output"]["message"] == "a"
    assert step["iterations"][1]["item"] == "b"
    assert step["iterations"][1]["output"]["message"] == "b"
    assert step["iterations"][2]["item"] == "c"
    assert step["iterations"][2]["output"]["message"] == "c"


def test_foreach_empty() -> None:
    """测试空列表时跳过"""
    flow_yaml = """
version: "1"
name: "foreach_empty_test"
steps:
  - id: "loop"
    action:
      type: "dummy.echo"
      params:
        message: "{{vars.item}}"
    for_each: "{{vars.items}}"
    for_item_var: "item"
""".lstrip()

    client = _client()
    resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"items": []}})
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "success"
    
    step = run["steps"][0]
    assert step["status"] == "success"
    # 空列表时，iterations 应该为空列表
    assert step["iterations"] is not None
    assert len(step["iterations"]) == 0


def test_foreach_with_output_var() -> None:
    """测试循环中使用 output_var"""
    flow_yaml = """
version: "1"
name: "foreach_output_var_test"
steps:
  - id: "loop"
    action:
      type: "dummy.echo"
      params:
        message: "{{vars.item}}"
    for_each: "{{vars.items}}"
    for_item_var: "item"
    output_var: "last_output"
""".lstrip()

    client = _client()
    resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"items": ["x", "y"]}})
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "success"
    
    step = run["steps"][0]
    assert step["status"] == "success"
    # action_output 应该是最后一次迭代的输出
    assert step["action_output"]["message"] == "y"
    # 验证 iterations
    assert step["iterations"] is not None
    assert len(step["iterations"]) == 2
    assert step["iterations"][0]["output"]["message"] == "x"
    assert step["iterations"][1]["output"]["message"] == "y"