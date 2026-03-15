# @file /backend/tests/test_condition.py
# @brief 娴嬭瘯鏉′欢鍒嗘敮鍔熻兘
# @create 2026-03-14

import pytest
from app.runtime.models import ActionSpec, FlowSpec, StepSpec
from app.runtime.runner.runner import evaluate_condition, resolve_templates


class TestEvaluateCondition:
    """娴嬭瘯 evaluate_condition 鍑芥暟"""

    def test_true_literal(self):
        """娴嬭瘯 true 瀛楅潰閲?""
        assert evaluate_condition("true") is True
        assert evaluate_condition("True") is True
        assert evaluate_condition("TRUE") is True

    def test_false_literal(self):
        """娴嬭瘯 false 瀛楅潰閲?""
        assert evaluate_condition("false") is False
        assert evaluate_condition("False") is False
        assert evaluate_condition("FALSE") is False

    def test_string_equal(self):
        """娴嬭瘯瀛楃涓茬浉绛夋瘮杈?=="""
        assert evaluate_condition('"hello" == "hello"') is True
        assert evaluate_condition('"hello" == "world"') is False
        assert evaluate_condition("'hello' == 'hello'") is True

    def test_string_not_equal(self):
        """娴嬭瘯瀛楃涓蹭笉鐩哥瓑姣旇緝 !="""
        assert evaluate_condition('"hello" != "world"') is True
        assert evaluate_condition('"hello" != "hello"') is False

    def test_number_greater(self):
        """娴嬭瘯鏁板瓧澶т簬 >"""
        assert evaluate_condition("10 > 5") is True
        assert evaluate_condition("5 > 10") is False
        assert evaluate_condition("5 > 5") is False

    def test_number_less(self):
        """娴嬭瘯鏁板瓧灏忎簬 <"""
        assert evaluate_condition("5 < 10") is True
        assert evaluate_condition("10 < 5") is False
        assert evaluate_condition("5 < 5") is False

    def test_number_greater_equal(self):
        """娴嬭瘯鏁板瓧澶т簬绛変簬 >="""
        assert evaluate_condition("10 >= 5") is True
        assert evaluate_condition("5 >= 5") is True
        assert evaluate_condition("4 >= 5") is False

    def test_number_less_equal(self):
        """娴嬭瘯鏁板瓧灏忎簬绛変簬 <="""
        assert evaluate_condition("5 <= 10") is True
        assert evaluate_condition("5 <= 5") is True
        assert evaluate_condition("10 <= 5") is False

    def test_unrecognized_expression(self):
        """娴嬭瘯鏃犳硶璇嗗埆鐨勮〃杈惧紡杩斿洖 False"""
        assert evaluate_condition("unknown") is False
        assert evaluate_condition("") is False


class TestConditionWithTemplates:
    """娴嬭瘯鏉′欢涓殑妯℃澘鍙橀噺瑙ｆ瀽"""

    def test_condition_with_vars_true(self):
        """娴嬭瘯鏉′欢涓娇鐢?{{vars.x}} 涓旀潯浠朵负 true"""
        condition = "{{vars.enabled}} == true"
        context = {"steps": {}, "vars": {"enabled": "true"}, "input": None}

        resolved = resolve_templates(condition, context)
        # 娉ㄦ剰锛歳esolve_templates 浼氬皢 "true" 瑙ｆ瀽涓哄瓧绗︿覆 "true"锛屼笉鏄竷灏斿€?        # 浣嗘垜浠殑 evaluate_condition 鏀寔瀛楃涓?"true"
        result = evaluate_condition(str(resolved))
        assert result is True

    def test_condition_with_vars_false(self):
        """娴嬭瘯鏉′欢涓娇鐢?{{vars.x}} 涓旀潯浠朵负 false"""
        condition = "{{vars.enabled}}"
        context = {"steps": {}, "vars": {"enabled": "false"}, "input": None}

        resolved = resolve_templates(condition, context)
        result = evaluate_condition(str(resolved))
        assert result is False


class TestStepSpecCondition:
    """娴嬭瘯 StepSpec.condition 瀛楁"""

    def test_condition_field_exists(self):
        """楠岃瘉 StepSpec 鏈?condition 瀛楁"""
        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={}),
            condition="true"
        )

        assert step.condition == "true"

    def test_condition_optional(self):
        """楠岃瘉 condition 鏄彲閫夌殑"""
        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={})
        )

        assert step.condition is None


class TestConditionIntegration:
    """鏉′欢鍒嗘敮闆嗘垚娴嬭瘯锛堜娇鐢?TestClient API锛?""

    def test_condition_true_executes_step(self):
        """鏉′欢涓?true 鏃讹紝step 姝ｅ父鎵ц"""
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
        """鏉′欢涓?false 鏃讹紝step 琚烦杩?""
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
        """鏉′欢寮曠敤鍙橀噺 {{vars.x}}"""
        from fastapi.testclient import TestClient
        from app.main import app

        # 娴嬭瘯鏉′欢涓?true 鐨勬儏鍐?        flow_yaml = """
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

        # 娴嬭瘯鏉′欢涓?false 鐨勬儏鍐?        flow_yaml2 = """
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
