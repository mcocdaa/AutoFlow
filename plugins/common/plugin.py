# @file /plugins/common/plugin.py
# @brief Plugin 抽象基类:声明式元信息 + 统一注册 + 配置/dry_run/错误共性 API
# @create 2026-08-10
# @update 2026-08-11 增加实例级 defaults/secrets、is_dry_run/setting/error_result,
#   actions/checks 实例属性化(Task 8 移除类属性兼容合并)

from __future__ import annotations

import os
from typing import Any

from app.core.registry import ActionContext, ActionHandler, CheckHandler, Registry

from plugins.common.helpers import is_truthy, resolve_env_value


class Plugin:
    """插件基类:声明式元信息 + 统一注册 + 配置/dry_run/错误共性 API"""

    name: str
    version: str = "0.1.0"
    dry_run_env: str | None = None
    actions: dict[str, ActionHandler] = {}  # 类属性默认(兼容旧 ABI);Task 8 移除
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))
        self.secrets = dict(self.config.get("secrets", {}))
        # 兼容过渡:复制子类类属性声明(旧 ABI);新 ABI 在子类 __init__ 覆盖为实例绑定方法
        self.actions: dict[str, ActionHandler] = dict(type(self).actions)
        self.checks: dict[str, CheckHandler] = dict(type(self).checks)

    def register(self, registry: Registry) -> None:
        """注册 plugin 元信息、actions、checks"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)

    # ---- 共性 API ----

    def is_dry_run(self, ctx: ActionContext, params: dict[str, Any]) -> bool:
        """统一 dry_run 判定:
        params.dry_run > ctx.vars.dry_run > 环境变量 dry_run_env
        """
        if "dry_run" in params:
            return is_truthy(params["dry_run"])
        if is_truthy(ctx.vars.get("dry_run")):
            return True
        if self.dry_run_env:
            return is_truthy(os.getenv(self.dry_run_env))
        return False

    def setting(
        self,
        params: dict[str, Any],
        key: str,
        *,
        env_var: str | None = None,
        default: Any = None,
    ) -> Any:
        """统一取值链:params[key] > defaults[key] > secrets[key]
        > os.getenv(env_var) > default

        env_var 仅当显式指定时参与;空字符串视为未设置继续回退;
        值为 "env:VAR" 形式时解析为环境变量值。
        """
        for source in (params, self.defaults, self.secrets):
            value = source.get(key)
            if value is not None:
                if isinstance(value, str) and not value.strip():
                    continue
                return resolve_env_value(value)
        if env_var is not None:
            value = os.getenv(env_var)
            if value:
                return resolve_env_value(value)
        return default

    def error_result(
        self, error: str, *, error_type: str = "unknown_error", **fields: Any
    ) -> dict[str, Any]:
        """统一错误返回构造:{"error":..., "error_type":..., **fields}"""
        return {"error": error, "error_type": error_type, **fields}
