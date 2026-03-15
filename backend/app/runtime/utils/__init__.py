# @file /backend/app/runtime/utils/__init__.py
# @brief 运行时工具模块
# @create 2026-03-15

from app.runtime.utils.condition import evaluate_condition
from app.runtime.utils.template import resolve_templates

__all__ = ["evaluate_condition", "resolve_templates"]
