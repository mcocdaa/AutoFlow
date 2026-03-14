# @file /backend/app/runtime/runner.py
# @brief 最小 Runner：按顺序执行 Flow 的 steps
# @create 2026-02-21 00:00:00

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.runtime.models import FlowSpec, RunResult, StepResult
from app.runtime.output_externalizer import externalize_if_large
from app.runtime.registry import ActionContext, CheckContext, Registry
from app.runtime.store import RunStore


def evaluate_condition(expr: str) -> bool:
    """
    简单的条件表达式评估，支持：
    - true / false (忽略大小写)
    - 字符串比较: "value" == "value", "a" != "b"
    - 数字比较: 10 > 5, 3 < 7, 5 >= 5, 2 <= 3
    
    不使用 eval()，使用简单的字符串解析。
    """
    expr = expr.strip()
    
    # 布尔值
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False
    
    # 字符串比较 == 或 !=
    # 格式: "abc" == "abc" 或 'abc' == 'abc'
    str_compare_match = re.match(r"^(.+?)\s*(==|!=)\s*(.+)$", expr)
    if str_compare_match:
        left = str_compare_match.group(1).strip()
        op = str_compare_match.group(2)
        right = str_compare_match.group(3).strip()
        
        # 去除引号
        if (left.startswith('"') and left.endswith('"')) or (left.startswith("'") and left.endswith("'")):
            left = left[1:-1]
        if (right.startswith('"') and right.endswith('"')) or (right.startswith("'") and right.endswith("'")):
            right = right[1:-1]
        
        if op == "==":
            return left == right
        else:  # !=
            return left != right
    
    # 数字比较 >, <, >=, <=
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
        else:  # <=
            return left <= right
    
    # 无法解析，返回 False
    return False


def resolve_templates(obj: Any, context: dict[str, Any]) -> Any:
    """
    解析模板变量，支持以下语法：
    - {{steps.X.output}} — 引用某个 step 的 action_output
    - {{vars.X}} — 引用 runtime_vars 中的变量
    - {{input}} — 引用当前 step 的 input
    """
    if isinstance(obj, str):
        def _serialize(value: Any) -> str:
            """Serialize a value for template substitution."""
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

            # {{steps.X.output}}
            steps_match = re.match(r'^steps\.(\w+)\.output$', template)
            if steps_match:
                step_id = steps_match.group(1)
                step_output = context.get("steps", {}).get(step_id)
                if step_output is not None:
                    return _serialize(step_output)
                return match.group(0)

            # {{vars.X}}
            vars_match = re.match(r'^vars\.(\w+)$', template)
            if vars_match:
                var_name = vars_match.group(1)
                var_value = context.get("vars", {}).get(var_name)
                if var_value is not None:
                    return _serialize(var_value)
                return match.group(0)

            # {{input}}
            if template == "input":
                input_value = context.get("input")
                if input_value is not None:
                    return _serialize(input_value)
                return match.group(0)

            return match.group(0)

        # Check if entire string is a single template (return typed value)
        single_match = re.fullmatch(r'\{\{(.+?)\}\}', obj.strip())
        if single_match:
            template = single_match.group(1).strip()
            # Resolve and return the raw typed value
            steps_match = re.match(r'^steps\.(\w+)\.output$', template)
            if steps_match:
                val = context.get("steps", {}).get(steps_match.group(1))
                if val is not None:
                    return val
            vars_match = re.match(r'^vars\.(\w+)$', template)
            if vars_match:
                val = context.get("vars", {}).get(vars_match.group(1))
                if val is not None:
                    return val
            if template == "input":
                val = context.get("input")
                if val is not None:
                    return val
            return obj  # no match, return original

        # Mixed string with templates embedded in text
        return re.sub(r'\{\{(.+?)\}\}', replace_template, obj)
    
    elif isinstance(obj, dict):
        return {k: resolve_templates(v, context) for k, v in obj.items()}
    
    elif isinstance(obj, list):
        return [resolve_templates(item, context) for item in obj]
    
    return obj


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Runner:
    def __init__(self, registry: Registry, store: RunStore) -> None:
        self._registry = registry
        self._store = store

    @property
    def artifacts_dir(self) -> Path:
        return self._store.artifacts_dir

    def run_flow(self, flow: FlowSpec, *, input: Any | None = None, vars: dict[str, Any] | None = None) -> RunResult:
        run_id = str(uuid.uuid4())
        run_artifacts_dir = self._store.artifacts_dir / run_id
        run_artifacts_dir.mkdir(parents=True, exist_ok=True)
        started_at = _utc_now()
        run = RunResult(run_id=run_id, flow_name=flow.name, status="running", started_at=started_at)
        self._store.save_run(run)

        current_input = input
        runtime_vars: dict[str, Any] = dict(vars or {})
        step_outputs: dict[str, Any] = {}  # 记录每个 step 的 action_output
        for step in flow.steps:
            # 条件分支检查
            if step.condition is not None:
                # 先解析条件表达式中的模板变量
                resolved_condition = resolve_templates(
                    step.condition,
                    {"steps": step_outputs, "vars": runtime_vars, "input": current_input}
                )
                # 评估条件
                if not evaluate_condition(str(resolved_condition)):
                    # 条件为 false，跳过该 step
                    step_started = _utc_now()
                    step_finished = _utc_now()
                    step_result = StepResult(
                        step_id=step.id,
                        status="skipped",
                        started_at=step_started,
                        finished_at=step_finished,
                        duration_ms=int((step_finished - step_started).total_seconds() * 1000),
                        action_output=None,
                        check_passed=None,
                        error=None,
                    )
                    run.steps.append(step_result)
                    self._store.save_run(run)
                    continue

            # 检查是否是 for 循环 step
            if step.for_each is not None:
                # 解析 for_each 获取列表
                loop_list = resolve_templates(
                    step.for_each,
                    {"steps": step_outputs, "vars": runtime_vars, "input": current_input}
                )
                # 确保是列表
                if not isinstance(loop_list, list):
                    loop_list = [loop_list]
                
                # 收集所有迭代结果
                iterations: list[dict] = []
                step_error: str | None = None
                action_output: Any | None = None
                check_passed: bool | None = None
                
                # 遍历列表执行
                for item in loop_list:
                    # 设置循环变量
                    runtime_vars[step.for_item_var] = item
                    
                    # 执行单个迭代
                    iter_started = _utc_now()
                    iter_error: str | None = None
                    iter_output: Any | None = None
                    iter_check_passed: bool | None = None
                    
                    attempts = step.retry.attempts if step.retry else 0
                    backoff = step.retry.backoff_seconds if step.retry else 0.0
                    
                    for attempt in range(max(1, attempts + 1)):
                        try:
                            resolved_params = resolve_templates(
                                step.action.params,
                                {"steps": step_outputs, "vars": runtime_vars, "input": current_input}
                            )
                            
                            action = self._registry.get_action(step.action.type)
                            iter_output = action(
                                ActionContext(
                                    run_id=run_id,
                                    step_id=step.id,
                                    input=current_input,
                                    vars=runtime_vars,
                                    artifacts_dir=run_artifacts_dir,
                                ),
                                resolved_params,
                            )
                            if step.check is not None:
                                check = self._registry.get_check(step.check.type)
                                iter_check_passed = check(
                                    CheckContext(run_id=run_id, step_id=step.id, action_output=iter_output, vars=runtime_vars),
                                    step.check.params,
                                )
                                if not iter_check_passed:
                                    raise RuntimeError(f"check failed: {step.check.type}")
                            iter_error = None
                            break
                        except Exception as e:
                            iter_error = str(e)
                            if attempt >= attempts:
                                break
                            if backoff > 0:
                                time.sleep(backoff * (2**attempt))
                    
                    iter_finished = _utc_now()
                    
                    # 记录迭代结果
                    iterations.append({
                        "item": item,
                        "output": iter_output,
                        "error": iter_error,
                        "check_passed": iter_check_passed,
                        "duration_ms": int((iter_finished - iter_started).total_seconds() * 1000),
                    })
                    
                    # 如果迭代出错，记录错误并停止
                    if iter_error is not None:
                        step_error = f"Iteration error for item '{item}': {iter_error}"
                        action_output = iter_output
                        break
                    
                    # 否则更新 action_output 为最后一次迭代的输出
                    action_output = iter_output
                
                step_started = _utc_now()
                step_finished = _utc_now()
                status: str = "success" if step_error is None else "failed"
                
                if action_output is not None:
                    action_output = externalize_if_large(action_output, artifacts_dir=run_artifacts_dir, file_stem=f"{step.id}.action_output")
                
                step_result = StepResult(
                    step_id=step.id,
                    status=status,  # type: ignore[arg-type]
                    started_at=step_started,
                    finished_at=step_finished,
                    duration_ms=int((step_finished - step_started).total_seconds() * 1000),
                    action_output=action_output,
                    check_passed=check_passed,
                    error=step_error,
                    iterations=iterations if step.for_each else None,
                )
                run.steps.append(step_result)
                self._store.save_run(run)

                if step_error is not None:
                    finished_at = _utc_now()
                    run.status = "failed"
                    run.finished_at = finished_at
                    run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                    run.error = step_error
                    self._store.save_run(run)
                    return run

                # 记录 step output
                step_outputs[step.id] = action_output
                if step.output_var is not None:
                    runtime_vars[step.output_var] = action_output

                current_input = action_output
                continue

            step_started = _utc_now()
            step_error: str | None = None
            action_output: Any | None = None
            check_passed: bool | None = None

            attempts = step.retry.attempts if step.retry else 0
            backoff = step.retry.backoff_seconds if step.retry else 0.0

            for attempt in range(max(1, attempts + 1)):
                try:
                    # 解析 action params 中的模板变量
                    resolved_params = resolve_templates(
                        step.action.params,
                        {"steps": step_outputs, "vars": runtime_vars, "input": current_input}
                    )
                    
                    action = self._registry.get_action(step.action.type)
                    action_output = action(
                        ActionContext(
                            run_id=run_id,
                            step_id=step.id,
                            input=current_input,
                            vars=runtime_vars,
                            artifacts_dir=run_artifacts_dir,
                        ),
                        resolved_params,
                    )
                    if step.check is not None:
                        check = self._registry.get_check(step.check.type)
                        check_passed = check(
                            CheckContext(run_id=run_id, step_id=step.id, action_output=action_output, vars=runtime_vars),
                            step.check.params,
                        )
                        if not check_passed:
                            raise RuntimeError(f"check failed: {step.check.type}")
                    step_error = None
                    break
                except Exception as e:
                    step_error = str(e)
                    if attempt >= attempts:
                        break
                    if backoff > 0:
                        time.sleep(backoff * (2**attempt))

            step_finished = _utc_now()
            status: str = "success" if step_error is None else "failed"

            action_output = externalize_if_large(action_output, artifacts_dir=run_artifacts_dir, file_stem=f"{step.id}.action_output")

            step_result = StepResult(
                step_id=step.id,
                status=status,  # type: ignore[arg-type]
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((step_finished - step_started).total_seconds() * 1000),
                action_output=action_output,
                check_passed=check_passed,
                error=step_error,
            )
            run.steps.append(step_result)
            self._store.save_run(run)

            if step_error is not None:
                finished_at = _utc_now()
                run.status = "failed"
                run.finished_at = finished_at
                run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                run.error = step_error
                self._store.save_run(run)
                return run

            # 记录 step output 到 step_outputs 和 runtime_vars
            step_outputs[step.id] = action_output
            if step.output_var is not None:
                runtime_vars[step.output_var] = action_output

            current_input = action_output

        finished_at = _utc_now()
        run.status = "success"
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        self._store.save_run(run)
        return run
