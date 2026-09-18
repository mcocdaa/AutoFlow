# @file /backend/app/runtime/utils/diff.py
# @brief 运行/JSON 深层差异工具(叶子级路径 + 步骤对齐)
# @create 2026-09-18

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.runtime.models import StepResult

DIFF_LIMIT = 100


def deep_diff(
    base: Any,
    target: Any,
    *,
    path: str = "$",
    limit: int = DIFF_LIMIT,
) -> list[dict[str, Any]]:
    """返回叶子级差异条目 [{path, base, target}]，最多 limit 条"""
    diffs: list[dict[str, Any]] = []
    _walk(base, target, path, diffs, limit)
    return diffs


def _walk(
    base: Any,
    target: Any,
    path: str,
    out: list[dict[str, Any]],
    limit: int,
) -> None:
    if len(out) >= limit or base == target:
        return
    if isinstance(base, dict) and isinstance(target, dict):
        for key in sorted(set(base) | set(target)):
            if len(out) >= limit:
                return
            next_path = f"{path}.{key}"
            if key not in base:
                out.append({"path": next_path, "base": None, "target": target[key]})
            elif key not in target:
                out.append({"path": next_path, "base": base[key], "target": None})
            else:
                _walk(base[key], target[key], next_path, out, limit)
        return
    if isinstance(base, list) and isinstance(target, list):
        if len(base) != len(target):
            out.append(
                {"path": f"{path}.length", "base": len(base), "target": len(target)}
            )
        pairs = zip(base, target, strict=False)
        for index, (base_item, target_item) in enumerate(pairs):
            if len(out) >= limit:
                return
            _walk(base_item, target_item, f"{path}[{index}]", out, limit)
        return
    out.append({"path": path, "base": base, "target": target})


def align_steps(
    base_steps: list[StepResult],
    target_steps: list[StepResult],
) -> list[tuple[int | None, StepResult | None, int | None, StepResult | None]]:
    """按 (step_id, 出现序号) 对齐两步序列:base 顺序在前,target 独有在后"""
    base_map: dict[tuple[str, int], tuple[int, StepResult]] = {}
    base_order: list[tuple[str, int]] = []
    counter: defaultdict[str, int] = defaultdict(int)
    for index, step in enumerate(base_steps):
        key = (step.step_id, counter[step.step_id])
        counter[step.step_id] += 1
        base_map[key] = (index, step)
        base_order.append(key)

    target_map: dict[tuple[str, int], tuple[int, StepResult]] = {}
    target_counter: defaultdict[str, int] = defaultdict(int)
    for index, step in enumerate(target_steps):
        key = (step.step_id, target_counter[step.step_id])
        target_counter[step.step_id] += 1
        target_map[key] = (index, step)

    aligned: list[
        tuple[int | None, StepResult | None, int | None, StepResult | None]
    ] = []
    for key in base_order:
        base_index, base_step = base_map[key]
        target_entry = target_map.get(key)
        if target_entry is None:
            aligned.append((base_index, base_step, None, None))
        else:
            aligned.append((base_index, base_step, target_entry[0], target_entry[1]))
    for key, (target_index, target_step) in target_map.items():
        if key not in base_map:
            aligned.append((None, None, target_index, target_step))
    return aligned


def step_diff(
    base_index: int | None,
    base_step: StepResult | None,
    target_index: int | None,
    target_step: StepResult | None,
    *,
    limit: int = DIFF_LIMIT,
) -> dict[str, Any]:
    """单个步骤对的差异描述(供 API 直接展开)"""
    base_output = base_step.action_output if base_step else None
    target_output = target_step.action_output if target_step else None
    output_diff = deep_diff(base_output, target_output, limit=limit)
    base_check = base_step.check_passed if base_step else None
    target_check = target_step.check_passed if target_step else None
    base_status = base_step.status if base_step else None
    target_status = target_step.status if target_step else None
    step_id = (
        base_step.step_id if base_step else (target_step.step_id if target_step else "")
    )
    return {
        "step_id": step_id,
        "base_index": base_index,
        "target_index": target_index,
        "base_status": base_status,
        "target_status": target_status,
        "status_changed": base_status != target_status,
        "base_check_passed": base_check,
        "target_check_passed": target_check,
        "check_changed": base_check != target_check,
        "base_error": base_step.error if base_step else None,
        "target_error": target_step.error if target_step else None,
        "output_changed": bool(output_diff) if base_step or target_step else False,
        "output_diff": output_diff,
    }
