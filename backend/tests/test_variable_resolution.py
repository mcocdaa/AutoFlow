# @file /backend/tests/test_variable_resolution.py
# @brief 娴嬭瘯鍙橀噺妯℃澘瑙ｆ瀽鍔熻兘
# @create 2026-03-14

import pytest
from app.runtime.runner.runner import resolve_templates


class TestResolveTemplates:
    """娴嬭瘯 resolve_templates 鍑芥暟"""

    def test_resolve_vars_reference(self):
        """娴嬭瘯 {{vars.X}} 寮曠敤"""
        context = {"steps": {}, "vars": {"name": "Alice", "age": 25}, "input": None}

        result = resolve_templates("Hello {{vars.name}}", context)
        assert result == "Hello Alice"

        # 鏁板瓧浼氳杞崲涓哄瓧绗︿覆
        result = resolve_templates("Age: {{vars.age}}", context)
        assert result == "Age: 25"

    def test_resolve_steps_output(self):
        """娴嬭瘯 {{steps.X.output}} 寮曠敤"""
        context = {
            "steps": {"step1": {"data": "hello"}, "step2": "world"},
            "vars": {},
            "input": None
        }

        result = resolve_templates("{{steps.step1.output}}", context)
        # Single template returns typed value (dict)
        assert result == {"data": "hello"}

        result = resolve_templates("{{steps.step2.output}}", context)
        assert result == "world"

    def test_resolve_input(self):
        """娴嬭瘯 {{input}} 寮曠敤"""
        context = {"steps": {}, "vars": {}, "input": {"message": "test"}}

        result = resolve_templates("Input: {{input}}", context)
        assert "test" in result

    def test_resolve_dict(self):
        """娴嬭瘯瀛楀吀涓殑妯℃澘瑙ｆ瀽"""
        context = {"steps": {}, "vars": {"value": "processed"}, "input": None}

        obj = {"url": "http://{{vars.value}}.com", "enabled": True}
        result = resolve_templates(obj, context)

        assert result["url"] == "http://processed.com"
        assert result["enabled"] is True

    def test_resolve_list(self):
        """娴嬭瘯鍒楄〃涓殑妯℃澘瑙ｆ瀽"""
        context = {"steps": {}, "vars": {"item": "foo"}, "input": None}

        obj = ["{{vars.item}}", "bar", 123]
        result = resolve_templates(obj, context)

        assert result[0] == "foo"
        assert result[1] == "bar"
        assert result[2] == 123

    def test_resolve_nested(self):
        """娴嬭瘯宓屽缁撴瀯"""
        context = {"steps": {"s1": "output"}, "vars": {"v1": "var1"}, "input": "in1"}

        obj = {
            "a": {
                "b": [
                    {"c": "{{steps.s1.output}}"},
                    {"d": "{{vars.v1}}"},
                    {"e": "{{input}}"}
                ]
            }
        }
        result = resolve_templates(obj, context)

        assert result["a"]["b"][0]["c"] == "output"
        assert result["a"]["b"][1]["d"] == "var1"
        assert result["a"]["b"][2]["e"] == "in1"

    def test_no_template(self):
        """娴嬭瘯鏃犳ā鏉挎椂淇濇寔鍘熸牱"""
        context = {"steps": {}, "vars": {}, "input": None}

        result = resolve_templates("no template here", context)
        assert result == "no template here"

        result = resolve_templates(123, context)
        assert result == 123

        result = resolve_templates(None, context)
        assert result is None

    def test_missing_reference(self):
        """娴嬭瘯寮曠敤涓嶅瓨鍦ㄦ椂淇濈暀鍘熸ā鏉?""
        context = {"steps": {}, "vars": {}, "input": None}

        result = resolve_templates("{{vars.unknown}}", context)
        assert result == "{{vars.unknown}}"

        result = resolve_templates("{{steps.missing.output}}", context)
        assert result == "{{steps.missing.output}}"


class TestStepSpecOutputVar:
    """娴嬭瘯 StepSpec.output_var 瀛楁锛堥渶瑕侀泦鎴愭祴璇曢獙璇侊級"""

    def test_output_var_field_exists(self):
        """楠岃瘉 StepSpec 鏈?output_var 瀛楁"""
        from app.runtime.models import ActionSpec, StepSpec

        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={}),
            output_var="my_result"
        )

        assert step.output_var == "my_result"

    def test_output_var_optional(self):
        """楠岃瘉 output_var 鏄彲閫夌殑"""
        from app.runtime.models import StepSpec, ActionSpec

        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={})
        )

        assert step.output_var is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
