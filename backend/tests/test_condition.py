# @file /backend/tests/test_condition.py
# @brief 测试条件分支功能
# @create 2026-03-14

import pytest
from app.runtime.models import FlowSpec, StepSpec, ActionSpec
from app.runtime.runner import evaluate_condition, resolve_templates


class TestEvaluateCondition:
    """测试 evaluate_condition 函数"""

    def test_true_literal(self):
        """测试 true 字面量"""
        assert evaluate_condition("true") is True
        assert evaluate_condition("True") is True
        assert evaluate_condition("TRUE") is True

    def test_false_literal(self):
        """测试 false 字面量"""
        assert evaluate_condition("false") is False
        assert evaluate_condition("False") is False
        assert evaluate_condition("FALSE") is False

    def test_string_equal(self):
        """测试字符串相等比较 =="""
        assert evaluate_condition('"hello" == "hello"') is True
        assert evaluate_condition('"hello" == "world"') is False
        assert evaluate_condition("'hello' == 'hello'") is True

    def test_string_not_equal(self):
        """测试字符串不相等比较 !="""
        assert evaluate_condition('"hello" != "world"') is True
        assert evaluate_condition('"hello" != "hello"') is False

    def test_number_greater(self):
        """测试数字大于 >"""
        assert evaluate_condition("10 > 5") is True
        assert evaluate_condition("5 > 10") is False
        assert evaluate_condition("5 > 5") is False

    def test_number_less(self):
        """测试数字小于 <"""
        assert evaluate_condition("5 < 10") is True
        assert evaluate_condition("10 < 5") is False
        assert evaluate_condition("5 < 5") is False

    def test_number_greater_equal(self):
        """测试数字大于等于 >="""
        assert evaluate_condition("10 >= 5") is True
        assert evaluate_condition("5 >= 5") is True
        assert evaluate_condition("4 >= 5") is False

    def test_number_less_equal(self):
        """测试数字小于等于 <="""
        assert evaluate_condition("5 <= 10") is True
        assert evaluate_condition("5 <= 5") is True
        assert evaluate_condition("10 <= 5") is False

    def test_unrecognized_expression(self):
        """测试无法识别的表达式返回 False"""
        assert evaluate_condition("unknown") is False
        assert evaluate_condition("") is False


class TestConditionWithTemplates:
    """测试条件中的模板变量解析"""

    def test_condition_with_vars_true(self):
        """测试条件中使用 {{vars.x}} 且条件为 true"""
        condition = "{{vars.enabled}} == true"
        context = {"steps": {}, "vars": {"enabled": "true"}, "input": None}
        
        resolved = resolve_templates(condition, context)
        # 注意：resolve_templates 会将 "true" 解析为字符串 "true"，不是布尔值
        # 但我们的 evaluate_condition 支持字符串 "true"
        result = evaluate_condition(str(resolved))
        assert result is True

    def test_condition_with_vars_false(self):
        """测试条件中使用 {{vars.x}} 且条件为 false"""
        condition = "{{vars.enabled}}"
        context = {"steps": {}, "vars": {"enabled": "false"}, "input": None}
        
        resolved = resolve_templates(condition, context)
        result = evaluate_condition(str(resolved))
        assert result is False


class TestStepSpecCondition:
    """测试 StepSpec.condition 字段"""

    def test_condition_field_exists(self):
        """验证 StepSpec 有 condition 字段"""
        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={}),
            condition="true"
        )
        
        assert step.condition == "true"

    def test_condition_optional(self):
        """验证 condition 是可选的"""
        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={})
        )
        
        assert step.condition is None


class TestConditionIntegration:
    """条件分支集成测试（使用 TestClient API）"""

    def test_condition_true_executes_step(self):
        """条件为 true 时，step 正常执行"""
        from fastapi.testclient import TestClient
        from app.main import app

        flow_yaml = """
version: "1"
name: "test_condition_true"
steps:
  - id: "step1"
    action:
      type: "dummy.echo"
      params:
        message: "executed"
    condition: "true"
""".lstrip()

        client = TestClient(app)
        resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml})
        assert resp.status_code == 200
        run = resp.json()
        
        assert run["status"] == "success"
        assert len(run["steps"]) == 1
        assert run["steps"][0]["status"] == "success"

    def test_condition_false_skips_step(self):
        """条件为 false 时，step 被跳过"""
        from fastapi.testclient import TestClient
        from app.main import app

        flow_yaml = """
version: "1"
name: "test_condition_false"
steps:
  - id: "step1"
    action:
      type: "dummy.echo"
      params:
        message: "should not see this"
    condition: "false"
""".lstrip()

        client = TestClient(app)
        resp = client.post("/api/v1/runs/execute", json={"flow_yaml": flow_yaml})
        assert resp.status_code == 200
        run = resp.json()
        
        assert run["status"] == "success"
        assert len(run["steps"]) == 1
        assert run["steps"][0]["status"] == "skipped"
        assert run["steps"][0]["action_output"] is None

    def test_condition_with_var(self):
        """条件引用变量 {{vars.x}}"""
        from fastapi.testclient import TestClient
        from app.main import app

        # 测试条件为 true 的情况
        flow_yaml = """
version: "1"
name: "test_condition_with_var"
steps:
  - id: "step1"
    action:
      type: "dummy.echo"
      params:
        message: "executed"
    condition: '{{vars.run_mode}} == "enabled"'
""".lstrip()

        client = TestClient(app)
        resp = client.post("/api/v1/runs/execute", json={
            "flow_yaml": flow_yaml,
            "vars": {"run_mode": "enabled"}
        })
        assert resp.status_code == 200
        run = resp.json()
        
        assert run["status"] == "success"
        assert len(run["steps"]) == 1
        assert run["steps"][0]["status"] == "success"

        # 测试条件为 false 的情况
        flow_yaml2 = """
version: "1"
name: "test_condition_with_var_false"
steps:
  - id: "step1"
    action:
      type: "dummy.echo"
      params:
        message: "should not see"
    condition: '{{vars.run_mode}} == "enabled"'
""".lstrip()

        resp2 = client.post("/api/v1/runs/execute", json={
            "flow_yaml": flow_yaml2,
            "vars": {"run_mode": "disabled"}
        })
        assert resp2.status_code == 200
        run2 = resp2.json()
        
        assert run2["status"] == "success"
        assert len(run2["steps"]) == 1
        assert run2["steps"][0]["status"] == "skipped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])