# @file /backend/tests/test_dag_actions.py
# @brief 测试 DAG Action 注册器和 log/set_var/wait actions
# @create 2026-04-01

from __future__ import annotations

import io
import sys
import time
from unittest.mock import patch

import pytest

from app.core.registry import ActionContext
from app.runtime.actions import (
    ActionRegistry,
    get_action_registry,
    log_action,
    register_builtin_actions,
    set_var_action,
    wait_action,
)


class TestActionRegistry:
    def test_registry_creation(self):
        """测试 ActionRegistry 创建"""
        registry = ActionRegistry()
        assert len(registry.list_actions()) == 0

    def test_register_action(self):
        """测试注册 Action"""
        registry = ActionRegistry()

        def test_handler(ctx, params):
            return {"result": params.get("value", 0)}

        registry.register("test", test_handler)
        assert "test" in registry.list_actions()

    def test_get_action(self):
        """测试获取已注册的 Action"""
        registry = ActionRegistry()

        def test_handler(ctx, params):
            return {"result": params.get("value", 0)}

        registry.register("test", test_handler)
        handler = registry.get("test")
        assert callable(handler)

    def test_get_nonexistent_action_raises_error(self):
        """测试获取不存在的 Action 抛出错误"""
        registry = ActionRegistry()
        with pytest.raises(ValueError, match="Action type 'nonexistent' not found"):
            registry.get("nonexistent")

    def test_list_actions(self):
        """测试列出所有注册的 Action"""
        registry = ActionRegistry()
        registry.register("action1", lambda ctx, params: {})
        registry.register("action3", lambda ctx, params: {})
        registry.register("action2", lambda ctx, params: {})
        actions = registry.list_actions()
        assert actions == sorted(["action1", "action2", "action3"])


class TestRegisterBuiltinActions:
    def test_register_builtin_actions(self):
        """测试注册内置 Actions"""
        registry = ActionRegistry()
        register_builtin_actions(registry)
        assert "log" in registry.list_actions()
        assert "set_var" in registry.list_actions()
        assert "wait" in registry.list_actions()

    def test_get_global_action_registry(self):
        """测试获取全局 Action 注册器"""
        registry = get_action_registry()
        assert isinstance(registry, ActionRegistry)
        assert "log" in registry.list_actions()
        assert "set_var" in registry.list_actions()
        assert "wait" in registry.list_actions()


class TestLogAction:
    def test_log_action_basic(self):
        """测试 log Action 基本功能"""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = log_action(ctx, {"message": "Hello, World!", "level": "info"})
            output = captured_output.getvalue().strip()
            assert "[info] Hello, World!" in output
            assert result == {
                "logged": True,
                "message": "Hello, World!",
                "level": "info",
            }
        finally:
            sys.stdout = sys.__stdout__

    def test_log_action_default_level(self):
        """测试 log Action 默认级别"""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = log_action(ctx, {"message": "Test message"})
            output = captured_output.getvalue().strip()
            assert "[info] Test message" in output
            assert result["level"] == "info"
        finally:
            sys.stdout = sys.__stdout__

    def test_log_action_empty_message(self):
        """测试 log Action 空消息"""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = log_action(ctx, {})
            output = captured_output.getvalue()
            assert "[info] " in output
            assert result["message"] == ""
        finally:
            sys.stdout = sys.__stdout__


class TestSetVarAction:
    def test_set_var_action_basic(self):
        """测试 set_var Action 基本功能"""
        ctx = ActionContext(
            run_id="test_run",
            step_id="step_1",
            input={},
            vars={},
            artifacts_dir="/tmp",
        )
        result = set_var_action(ctx, {"name": "my_var", "value": "test_value"})
        assert ctx.vars["my_var"] == "test_value"
        assert result == {"name": "my_var", "value": "test_value"}

    def test_set_var_action_update_existing(self):
        """测试 set_var Action 更新已存在的变量"""
        ctx = ActionContext(
            run_id="test_run",
            step_id="step_1",
            input={},
            vars={"my_var": "old_value"},
            artifacts_dir="/tmp",
        )
        result = set_var_action(ctx, {"name": "my_var", "value": "new_value"})
        assert ctx.vars["my_var"] == "new_value"
        assert result == {"name": "my_var", "value": "new_value"}

    def test_set_var_action_missing_name_raises_error(self):
        """测试 set_var Action 缺少变量名抛出错误"""
        ctx = ActionContext(
            run_id="test_run",
            step_id="step_1",
            input={},
            vars={},
            artifacts_dir="/tmp",
        )
        with pytest.raises(ValueError, match="Variable name is required"):
            set_var_action(ctx, {"value": "test_value"})

    def test_set_var_action_complex_value(self):
        """测试 set_var Action 设置复杂类型值"""
        complex_value = {"key": "value", "list": [1, 2, 3]}
        ctx = ActionContext(
            run_id="test_run",
            step_id="step_1",
            input={},
            vars={},
            artifacts_dir="/tmp",
        )
        result = set_var_action(ctx, {"name": "complex", "value": complex_value})
        assert ctx.vars["complex"] == complex_value
        assert result == {"name": "complex", "value": complex_value}


class TestWaitAction:
    def test_wait_action_basic(self):
        """测试 wait Action 基本功能"""
        with patch("time.sleep") as mock_sleep:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = wait_action(ctx, {"seconds": 2.5})
            mock_sleep.assert_called_once_with(2.5)
            assert result == {"waited_seconds": 2.5}

    def test_wait_action_default_seconds(self):
        """测试 wait Action 默认等待时间"""
        with patch("time.sleep") as mock_sleep:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = wait_action(ctx, {})
            mock_sleep.assert_called_once_with(1.0)
            assert result == {"waited_seconds": 1.0}

    def test_wait_action_zero_seconds(self):
        """测试 wait Action 等待 0 秒"""
        with patch("time.sleep") as mock_sleep:
            ctx = ActionContext(
                run_id="test_run",
                step_id="step_1",
                input={},
                vars={},
                artifacts_dir="/tmp",
            )
            result = wait_action(ctx, {"seconds": 0})
            mock_sleep.assert_called_once_with(0.0)
            assert result == {"waited_seconds": 0.0}

    def test_wait_action_negative_seconds_raises_error(self):
        """测试 wait Action 负数秒数抛出错误"""
        ctx = ActionContext(
            run_id="test_run",
            step_id="step_1",
            input={},
            vars={},
            artifacts_dir="/tmp",
        )
        with pytest.raises(ValueError, match="Seconds must be non-negative"):
            wait_action(ctx, {"seconds": -1})
