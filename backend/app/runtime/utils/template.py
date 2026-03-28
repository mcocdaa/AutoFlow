# @file /backend/app/runtime/utils/template.py
# @brief 模板变量解析
# @create 2026-03-15
# @update 2026-03-15 修复循环引用问题 - 返回副本而非原始引用

import copy
import json
import re
from typing import Any


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

            steps_match = re.match(r"^steps\.(\w+)\.output$", template)
            if steps_match:
                step_id = steps_match.group(1)
                step_output = context.get("steps", {}).get(step_id)
                if step_output is not None:
                    return _serialize(copy.deepcopy(step_output))
                return match.group(0)

            vars_match = re.match(r"^vars\.(\w+)$", template)
            if vars_match:
                var_name = vars_match.group(1)
                var_value = context.get("vars", {}).get(var_name)
                if var_value is not None:
                    return _serialize(copy.deepcopy(var_value))
                return match.group(0)

            if template == "input":
                input_value = context.get("input")
                if input_value is not None:
                    return _serialize(copy.deepcopy(input_value))
                return match.group(0)

            return match.group(0)

        single_match = re.fullmatch(r"\{\{(.+?)\}\}", obj.strip())
        if single_match:
            template = single_match.group(1).strip()
            steps_match = re.match(r"^steps\.(\w+)\.output$", template)
            if steps_match:
                val = context.get("steps", {}).get(steps_match.group(1))
                if val is not None:
                    return copy.deepcopy(val)
            vars_match = re.match(r"^vars\.(\w+)$", template)
            if vars_match:
                val = context.get("vars", {}).get(vars_match.group(1))
                if val is not None:
                    return copy.deepcopy(val)
            if template == "input":
                val = context.get("input")
                if val is not None:
                    return copy.deepcopy(val)
            return obj

        return re.sub(r"\{\{(.+?)\}\}", replace_template, obj)

    elif isinstance(obj, dict):
        return {k: resolve_templates(v, context) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [resolve_templates(item, context) for item in obj]

    return obj
