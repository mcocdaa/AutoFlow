# @file /backend/app/runtime/runner/runner.py
# @brief Flow 执行器
# @create 2026-02-21 00:00:00
# @update 2026-03-15 拆分条件与模板解析到独立模块
# @update 2026-08-08 合并 for_each 与普通步骤双路径,修复 duration_ms / check_passed

from __future__ import annotations

import copy
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry
from app.runtime.models import FlowSpec, HookSpec, RunResult, StepResult, StepSpec
from app.runtime.storage.store import RunStore
from app.runtime.utils import evaluate_condition, resolve_templates
from app.runtime.utils.output_externalizer import externalize_if_large


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_vars_value(value: Any) -> Any:
    """将 action 输出转为可存入 runtime_vars 的值(JSON 往返打断循环引用)"""
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


def _deep_copy_or_str(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:
        return str(value)


class Runner:
    def __init__(self, registry: Registry, store: RunStore) -> None:
        self._registry = registry
        self._store = store

    @property
    def artifacts_dir(self) -> Path:
        return self._store.artifacts_dir

    def _run_hooks(
        self,
        hooks: HookSpec,
        run_id: str,
        run_artifacts_dir: Path,
        runtime_vars: dict[str, Any],
        step_outputs: dict[str, Any],
        current_input: Any,
        status: str,
    ) -> None:
        """执行 flow hooks"""
        hook_actions = []
        if status == "success" and hooks.on_success:
            hook_actions = hooks.on_success
        elif status == "failed" and hooks.on_failure:
            hook_actions = hooks.on_failure

        for hook_action in hook_actions:
            try:
                resolved_params = resolve_templates(
                    hook_action.params,
                    {
                        "steps": step_outputs,
                        "vars": runtime_vars,
                        "input": current_input,
                    },
                )
                handler = self._registry.get_action(hook_action.type)
                if handler:
                    ctx = ActionContext(
                        run_id=run_id,
                        step_id="__hook__",
                        input=current_input,
                        vars=runtime_vars,
                        artifacts_dir=run_artifacts_dir,
                    )
                    handler(ctx, resolved_params)
            except Exception:
                # hook 执行失败不影响主流程状态
                pass

    def _execute_once(
        self,
        *,
        run_id: str,
        step: StepSpec,
        current_input: Any,
        runtime_vars: dict[str, Any],
        step_outputs: dict[str, Any],
        run_artifacts_dir: Path,
    ) -> tuple[Any, bool | None, str | None]:
        """执行一次 action(+check),失败按 retry 配置重试

        Returns:
            (output, check_passed, error)
        """
        output: Any | None = None
        check_passed: bool | None = None
        error: str | None = None

        attempts = step.retry.attempts if step.retry else 0
        backoff = step.retry.backoff_seconds if step.retry else 0.0

        for attempt in range(max(1, attempts + 1)):
            try:
                resolved_params = resolve_templates(
                    step.action.params,
                    {
                        "steps": step_outputs,
                        "vars": runtime_vars,
                        "input": current_input,
                    },
                )

                action = self._registry.get_action(step.action.type)
                output = action(
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
                        CheckContext(
                            run_id=run_id,
                            step_id=step.id,
                            action_output=output,
                            vars=runtime_vars,
                        ),
                        step.check.params,
                    )
                    if not check_passed:
                        raise RuntimeError(f"check failed: {step.check.type}")
                return output, check_passed, None
            except Exception as e:
                error = str(e)
                if attempt >= attempts:
                    break
                if backoff > 0:
                    time.sleep(backoff * (2**attempt))

        return output, check_passed, error

    def _execute_step(
        self,
        *,
        run_id: str,
        step: StepSpec,
        current_input: Any,
        runtime_vars: dict[str, Any],
        step_outputs: dict[str, Any],
        run_artifacts_dir: Path,
    ) -> tuple[list[dict] | None, Any, bool | None, bool, str | None]:
        """执行单个 step(for_each 时对每个 item 执行并收集 iterations)

        Returns:
            (iterations, action_output, check_passed, success, step_error)
        """
        iterations: list[dict] | None = None
        step_error: str | None = None
        action_output: Any | None = None
        check_passed: bool | None = None

        if step.for_each is not None:
            iterations = []
            loop_list = resolve_templates(
                step.for_each,
                {
                    "steps": step_outputs,
                    "vars": runtime_vars,
                    "input": current_input,
                },
            )
            if not isinstance(loop_list, list):
                loop_list = [loop_list]

            for item in loop_list:
                runtime_vars[step.for_item_var] = item

                iter_started = _utc_now()
                iter_output, iter_check_passed, iter_error = self._execute_once(
                    run_id=run_id,
                    step=step,
                    current_input=current_input,
                    runtime_vars=runtime_vars,
                    step_outputs=step_outputs,
                    run_artifacts_dir=run_artifacts_dir,
                )
                iter_finished = _utc_now()

                runtime_vars_clean = {
                    k: v for k, v in runtime_vars.items() if k != step.for_item_var
                }

                iterations.append(
                    {
                        "item": item,
                        "output": _deep_copy_or_str(iter_output),
                        "error": iter_error,
                        "check_passed": iter_check_passed,
                        "duration_ms": int(
                            (iter_finished - iter_started).total_seconds() * 1000
                        ),
                        "vars_snapshot": _deep_copy_or_str(runtime_vars_clean),
                    }
                )

                action_output = iter_output
                if iter_check_passed is not None:
                    check_passed = iter_check_passed
                if iter_error is not None:
                    step_error = f"Iteration error for item '{item}': {iter_error}"
                    break
        else:
            action_output, check_passed, step_error = self._execute_once(
                run_id=run_id,
                step=step,
                current_input=current_input,
                runtime_vars=runtime_vars,
                step_outputs=step_outputs,
                run_artifacts_dir=run_artifacts_dir,
            )

        success = step_error is None
        return iterations, action_output, check_passed, success, step_error

    def run_flow(
        self,
        flow: FlowSpec,
        *,
        input: Any | None = None,
        vars: dict[str, Any] | None = None,
    ) -> RunResult:
        run_id = str(uuid.uuid4())
        run_artifacts_dir = self._store.artifacts_dir / run_id
        run_artifacts_dir.mkdir(parents=True, exist_ok=True)
        started_at = _utc_now()
        run = RunResult(
            run_id=run_id, flow_name=flow.name, status="running", started_at=started_at
        )
        self._store.save_run(run)

        current_input = input
        runtime_vars: dict[str, Any] = copy.deepcopy(dict(vars or {}))
        step_outputs: dict[str, Any] = {}
        for step in flow.steps:
            step_started = _utc_now()

            if step.condition is not None:
                resolved_condition = resolve_templates(
                    step.condition,
                    {
                        "steps": step_outputs,
                        "vars": runtime_vars,
                        "input": current_input,
                    },
                )
                if not evaluate_condition(str(resolved_condition)):
                    step_finished = _utc_now()
                    step_result = StepResult(
                        step_id=step.id,
                        status="skipped",
                        started_at=step_started,
                        finished_at=step_finished,
                        duration_ms=int(
                            (step_finished - step_started).total_seconds() * 1000
                        ),
                        action_output=None,
                        check_passed=None,
                        error=None,
                    )
                    run.steps.append(step_result)
                    self._store.save_run(run)
                    continue

            step_result, action_output, check_passed, success, step_error = (
                self._execute_step(
                    run_id=run_id,
                    step=step,
                    current_input=current_input,
                    runtime_vars=runtime_vars,
                    step_outputs=step_outputs,
                    run_artifacts_dir=run_artifacts_dir,
                )
            )

            step_finished = _utc_now()
            if action_output is not None:
                action_output = externalize_if_large(
                    action_output,
                    artifacts_dir=run_artifacts_dir,
                    file_stem=f"{step.id}.action_output",
                )

            run.steps.append(
                StepResult(
                    step_id=step.id,
                    status="success" if success else "failed",
                    started_at=step_started,
                    finished_at=step_finished,
                    duration_ms=int(
                        (step_finished - step_started).total_seconds() * 1000
                    ),
                    action_output=action_output,
                    check_passed=check_passed,
                    error=step_error,
                    iterations=step_result,
                )
            )
            self._store.save_run(run)

            if step_error is not None:
                finished_at = _utc_now()
                run.status = "failed"
                run.finished_at = finished_at
                run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                run.error = step_error
                self._store.save_run(run)
                if flow.hooks:
                    self._run_hooks(
                        flow.hooks,
                        run_id,
                        run_artifacts_dir,
                        runtime_vars,
                        step_outputs,
                        current_input,
                        "failed",
                    )
                return run

            step_outputs[step.id] = action_output
            if step.output_var is not None:
                runtime_vars[step.output_var] = _to_vars_value(action_output)

            current_input = action_output

        finished_at = _utc_now()
        run.status = "success"
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        self._store.save_run(run)
        if flow.hooks:
            self._run_hooks(
                flow.hooks,
                run_id,
                run_artifacts_dir,
                runtime_vars,
                step_outputs,
                current_input,
                "success",
            )
        return run
