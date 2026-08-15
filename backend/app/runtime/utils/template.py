# @file /backend/app/runtime/utils/template.py
# @brief 模板变量解析
# @create 2026-03-15
# @update 2026-03-15 修复循环引用问题 - 返回副本而非原始引用
# @update 2026-08-15 支持属性链引用 {{steps.X.output.key}} / {{vars.X.y}} / {{input.x}}

import copy
import json
import re
from typing import Any

_MISSING = object()


def _get_path(value: Any, parts: list[str]) -> Any:
    """按属性链逐级取值,支持 dict 键与 list 索引;缺失返回 _MISSING"""
    current = value
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


_STEPS_RE = re.compile(r"^steps\.(\w+)\.output(?:\.(.+))?$")
_VARS_RE = re.compile(r"^vars\.(\w+)(?:\.(.+))?$")
_INPUT_RE = re.compile(r"^input(?:\.(.+))?$")


def _lookup(template: str, context: dict[str, Any]) -> Any:
    """解析单个模板引用,返回 (found, value);found=False 表示引用或路径缺失"""
    steps_match = _STEPS_RE.match(template)
    if steps_match:
        step_output = context.get("steps", {}).get(steps_match.group(1))
        if step_output is None:
            return False, None
        parts = steps_match.group(2).split(".") if steps_match.group(2) else []
        val = _get_path(step_output, parts)
        return (False, None) if val is _MISSING else (True, copy.deepcopy(val))

    vars_match = _VARS_RE.match(template)
    if vars_match:
        var_value = context.get("vars", {}).get(vars_match.group(1))
        if var_value is None:
            return False, None
        parts = vars_match.group(2).split(".") if vars_match.group(2) else []
        val = _get_path(var_value, parts)
        return (False, None) if val is _MISSING else (True, copy.deepcopy(val))

    input_match = _INPUT_RE.match(template)
    if input_match:
        input_value = context.get("input")
        if input_value is None:
            return False, None
        parts = input_match.group(1).split(".") if input_match.group(1) else []
        val = _get_path(input_value, parts)
        return (False, None) if val is _MISSING else (True, copy.deepcopy(val))

    return False, None


def resolve_templates(obj: Any, context: dict[str, Any]) -> Any:
    if isinstance(obj, str):

        def _serialize(value: Any) -> str:
            if isinstance(value, str):
                return value
            if isinstance(value, (int, float, bool)):
                return str(value)
            try:
                return json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(value)

        def replace_template(match):
            template = match.group(1).strip()
            found, value = _lookup(template, context)
            if found:
                return _serialize(value)
            return match.group(0)

        single_match = re.fullmatch(r"\{\{(.+?)\}\}", obj.strip())
        if single_match:
            template = single_match.group(1).strip()
            found, value = _lookup(template, context)
            if found:
                return value
            return obj

        return re.sub(r"\{\{(.+?)\}\}", replace_template, obj)

    elif isinstance(obj, dict):
        return {k: resolve_templates(v, context) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [resolve_templates(item, context) for item in obj]

    return obj
