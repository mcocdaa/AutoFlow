from __future__ import annotations

import copy
from typing import Any


def _deep_copy_with_ref_tracking(obj: Any, seen: dict[int, Any] | None = None) -> Any:
    """带引用跟踪的深拷贝函数，解决循环引用问题

    Args:
        obj: 要拷贝的对象
        seen: 已访问对象的ID映射（内部使用）

    Returns:
        拷贝后的对象
    """
    if seen is None:
        seen = {}

    obj_id = id(obj)
    if obj_id in seen:
        return seen[obj_id]

    if isinstance(obj, dict):
        result = {}
        seen[obj_id] = result
        for k, v in obj.items():
            result[k] = _deep_copy_with_ref_tracking(v, seen)
        return result

    if isinstance(obj, list):
        result = []
        seen[obj_id] = result
        for item in obj:
            result.append(_deep_copy_with_ref_tracking(item, seen))
        return result

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    try:
        return copy.deepcopy(obj)
    except Exception:
        return str(obj)
