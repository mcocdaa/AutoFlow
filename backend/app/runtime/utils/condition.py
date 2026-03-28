# @file /backend/app/runtime/utils/condition.py
# @brief 条件表达式求值
# @create 2026-03-15

import re


def evaluate_condition(expr: str) -> bool:
    expr = expr.strip()
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False

    str_compare_match = re.match(r"^(.+?)\s*(==|!=)\s*(.+)$", expr)
    if str_compare_match:
        left = str_compare_match.group(1).strip()
        op = str_compare_match.group(2)
        right = str_compare_match.group(3).strip()

        if (left.startswith('"') and left.endswith('"')) or (
            left.startswith("'") and left.endswith("'")
        ):
            left = left[1:-1]
        if (right.startswith('"') and right.endswith('"')) or (
            right.startswith("'") and right.endswith("'")
        ):
            right = right[1:-1]

        if op == "==":
            return left == right
        else:
            return left != right

    num_compare_match = re.match(r"^(-?\d+\.?\d*)\s*(>=|<=|>|<)\s*(-?\d+\.?\d*)$", expr)
    if num_compare_match:
        left = float(num_compare_match.group(1))
        op = num_compare_match.group(2)
        right = float(num_compare_match.group(3))

        if op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        else:
            return left <= right

    return False
