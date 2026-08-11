# @file /backend/app/runtime/utils/serialization.py
# @brief 序列化/深拷贝统一工具:引用跟踪打断循环引用,无法序列化的值退化为 str
# @create 2026-08-10

from __future__ import annotations

import copy
import json
from typing import Any


def safe_deep_copy(value: Any) -> Any:
    """深拷贝,引用跟踪打断循环引用;无法拷贝的容器成员退化为 str

    统一替换原 store._deep_copy_with_ref_tracking 与 runner._deep_copy_or_str。
    dict/list 递归拷贝(共享引用保持),基本类型原样返回,
    其余对象经 copy.deepcopy,失败时退化为 str(value)。
    """
    seen: dict[int, Any] = {}

    def _copy(obj: Any) -> Any:
        obj_id = id(obj)
        if obj_id in seen:
            return seen[obj_id]

        if isinstance(obj, dict):
            result: dict[Any, Any] = {}
            seen[obj_id] = result
            for k, v in obj.items():
                result[k] = _copy(v)
            return result

        if isinstance(obj, list):
            result: list[Any] = []
            seen[obj_id] = result
            for item in obj:
                result.append(_copy(item))
            return result

        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        try:
            return copy.deepcopy(obj)
        except Exception:
            return str(obj)

    return _copy(value)


def to_jsonable(value: Any) -> Any:
    """JSON 往返打断循环引用,无法序列化的值经 default=str 处理

    统一替换 runner._to_vars_value。dumps 整体失败时退化为 str(value)。
    """
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)
