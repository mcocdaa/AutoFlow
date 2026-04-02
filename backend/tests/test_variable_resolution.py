# @file /backend/tests/test_variable_resolution.py
# @brief 测试变量模板解析功能
# @create 2026-03-14

import pytest

from app.runtime.utils import resolve_templates


class TestResolveTemplates:
    """测试 resolve_templates 函数"""

    def test_resolve_vars_reference(self):
        """测试 {{vars.X}} 引用"""
        context = {"steps": {}, "vars": {"name": "Alice", "age": 25}, "input": None}

        result = resolve_templates("Hello {{vars.name}}", context)
        assert result == "Hello Alice"

        # 数字会被转换为字符串
        result = resolve_templates("Age: {{vars.age}}", context)
        assert result == "Age: 25"

    def test_resolve_steps_output(self):
        """测试 {{steps.X.output}} 引用"""
        context = {
            "steps": {"step1": {"data": "hello"}, "step2": "world"},
            "vars": {},
            "input": None,
        }

        result = resolve_templates("{{steps.step1.output}}", context)
        # Single template returns typed value (dict)
        assert result == {"data": "hello"}

        result = resolve_templates("{{steps.step2.output}}", context)
        assert result == "world"

    def test_resolve_input(self):
        """测试 {{input}} 引用"""
        context = {"steps": {}, "vars": {}, "input": {"message": "test"}}

        result = resolve_templates("Input: {{input}}", context)
        assert "test" in result

    def test_resolve_dict(self):
        """测试字典中的模板解析"""
        context = {"steps": {}, "vars": {"value": "processed"}, "input": None}

        obj = {"url": "http://{{vars.value}}.com", "enabled": True}
        result = resolve_templates(obj, context)

        assert result["url"] == "http://processed.com"
        assert result["enabled"] is True

    def test_resolve_list(self):
        """测试列表中的模板解析"""
        context = {"steps": {}, "vars": {"item": "foo"}, "input": None}

        obj = ["{{vars.item}}", "bar", 123]
        result = resolve_templates(obj, context)

        assert result[0] == "foo"
        assert result[1] == "bar"
        assert result[2] == 123

    def test_resolve_nested(self):
        """测试嵌套结构"""
        context = {"steps": {"s1": "output"}, "vars": {"v1": "var1"}, "input": "in1"}

        obj = {
            "a": {
                "b": [
                    {"c": "{{steps.s1.output}}"},
                    {"d": "{{vars.v1}}"},
                    {"e": "{{input}}"},
                ]
            }
        }
        result = resolve_templates(obj, context)

        assert result["a"]["b"][0]["c"] == "output"
        assert result["a"]["b"][1]["d"] == "var1"
        assert result["a"]["b"][2]["e"] == "in1"

    def test_no_template(self):
        """测试无模板时保持原样"""
        context = {"steps": {}, "vars": {}, "input": None}

        result = resolve_templates("no template here", context)
        assert result == "no template here"

        result = resolve_templates(123, context)
        assert result == 123

        result = resolve_templates(None, context)
        assert result is None

    def test_missing_reference(self):
        """测试引用不存在时保留原模板"""
        context = {"steps": {}, "vars": {}, "input": None}

        result = resolve_templates("{{vars.unknown}}", context)
        assert result == "{{vars.unknown}}"

        result = resolve_templates("{{steps.missing.output}}", context)
        assert result == "{{steps.missing.output}}"


class TestStepSpecOutputVar:
    """测试 StepSpec.output_var 字段（需要集成测试验证）"""

    def test_output_var_field_exists(self):
        """验证 StepSpec 有 output_var 字段"""
        from app.runtime.models import ActionSpec, StepSpec

        step = StepSpec(
            id="test_step",
            action=ActionSpec(type="test", params={}),
            output_var="my_result",
        )

        assert step.output_var == "my_result"

    def test_output_var_optional(self):
        """验证 output_var 是可选的"""
        from app.runtime.models import ActionSpec, StepSpec

        step = StepSpec(id="test_step", action=ActionSpec(type="test", params={}))

        assert step.output_var is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
