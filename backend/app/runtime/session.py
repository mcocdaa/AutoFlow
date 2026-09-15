# @file /backend/app/runtime/session.py
# @brief 可暂停的 Flow 执行会话(整条执行与调试单步共用同一实现)
# @create 2026-09-15

from __future__ import annotations

import copy
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry
from app.runtime.models import (
    ActionSpec,
    FlowSpec,
    HookPhase,
    HookResult,
    HookSpec,
    RunResult,
    StepResult,
    StepSpec,
)
from app.runtime.storage.store import RunStore
from app.runtime.utils import evaluate_condition, resolve_templates
from app.runtime.utils.output_externalizer import externalize_if_large
from app.runtime.utils.serialization import safe_deep_copy, to_jsonable

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RunSession:
    """可暂停的执行会话

    整条执行(Runner.run_flow)与调试单步(Debug API)共用该类:
    - step(): 执行下一个待执行步骤
    - run_to_completion(): 执行到底并触发 hooks
    - to_state()/from_state(): JSON 状态序列化,支持跨 worker 恢复
    """

    def __init__(
        self,
        registry: Registry,
        store: RunStore,
        flow: FlowSpec,
        *,
        run: RunResult,
        request: dict[str, Any] | None = None,
        runtime_vars: dict[str, Any] | None = None,
        step_outputs: dict[str, Any] | None = None,
        current_input: Any = None,
        index: int = 0,
    ) -> None:
        self._registry = registry
        self._store = store
        self._flow = flow
        self._request = request
        self._run = run
        self._runtime_vars: dict[str, Any] = runtime_vars or {}
        self._step_outputs: dict[str, Any] = step_outputs or {}
        self._current_input = current_input
        self._index = index
        self._started_at = run.started_at
        self._finished = run.status != "running"

    @classmethod
    def start(
        cls,
        registry: Registry,
        store: RunStore,
        flow: FlowSpec,
        *,
        input: Any = None,
        vars: dict[str, Any] | None = None,
        request: dict[str, Any] | None = None,
    ) -> RunSession:
        """创建新会话:初始化 run 与产物目录"""
        run_id = str(uuid.uuid4())
        run_artifacts_dir = store.artifacts_dir / run_id
        run_artifacts_dir.mkdir(parents=True, exist_ok=True)
        run = RunResult(
            run_id=run_id,
            flow_name=flow.name,
            status="running",
            started_at=_utc_now(),
        )
        store.save_run(run)
        return cls(
            registry,
            store,
            flow,
            run=run,
            request=request,
            runtime_vars=copy.deepcopy(dict(vars or {})),
            current_input=input,
        )

    @property
    def run(self) -> RunResult:
        return self._run

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def index(self) -> int:
        return self._index

    @property
    def hook_results(self) -> list[HookResult]:
        return list(self._run.hook_results)

    @property
    def run_artifacts_dir(self) -> Path:
        return self._store.artifacts_dir / self._run.run_id

    def planned_steps(self) -> list[dict[str, Any]]:
        """计划步骤信息(供调试快照展示,不包含执行结果)"""
        return [
            {
                "id": step.id,
                "name": step.name,
                "for_each": step.for_each,
                "has_condition": step.condition is not None,
                "retry_attempts": step.retry.attempts if step.retry else 0,
                "output_var": step.output_var,
            }
            for step in self._flow.steps
        ]

    def step(self) -> None:
        """执行下一个待执行步骤(已结束则幂等返回)"""
        if self._finished:
            return
        if self._index >= len(self._flow.steps):
            self._finalize(status="success")
            return

        step = self._flow.steps[self._index]
        step_started = _utc_now()

        if step.condition is not None:
            resolved_condition = resolve_templates(
                step.condition,
                self._template_context(),
            )
            if not evaluate_condition(str(resolved_condition)):
                step_finished = _utc_now()
                self._run.steps.append(
                    self._make_step_result(
                        step_id=step.id,
                        status="skipped",
                        started_at=step_started,
                        finished_at=step_finished,
                        action_output=None,
                        check_passed=None,
                        error=None,
                    )
                )
                self._store.save_run(self._run)
                self._index += 1
                if self._index >= len(self._flow.steps):
                    self._finalize(status="success")
                return

        iterations, action_output, check_passed, success, step_error = (
            self._execute_step(step)
        )

        step_finished = _utc_now()
        if action_output is not None:
            action_output = externalize_if_large(
                action_output,
                artifacts_dir=self.run_artifacts_dir,
                file_stem=f"{step.id}.action_output",
            )

        self._run.steps.append(
            self._make_step_result(
                step_id=step.id,
                status="success" if success else "failed",
                started_at=step_started,
                finished_at=step_finished,
                action_output=action_output,
                check_passed=check_passed,
                error=step_error,
                iterations=iterations,
            )
        )
        self._store.save_run(self._run)

        if step_error is not None:
            self._finalize(status="failed", error=step_error)
            return

        self._step_outputs[step.id] = action_output
        if step.output_var is not None:
            self._runtime_vars[step.output_var] = to_jsonable(action_output)

        self._current_input = action_output
        self._index += 1
        if self._index >= len(self._flow.steps):
            self._finalize(status="success")

    def run_to_completion(self) -> RunResult:
        """执行到底并触发 hooks,返回最终 run"""
        while not self._finished:
            self.step()
        return self._run

    def to_state(self) -> dict[str, Any]:
        """完整会话状态(JSON 可序列化),用于落盘/跨 worker 恢复"""
        return {
            "flow": self._flow.model_dump(mode="json"),
            "request": to_jsonable(self._request),
            "runtime_vars": to_jsonable(self._runtime_vars),
            "step_outputs": to_jsonable(self._step_outputs),
            "current_input": to_jsonable(self._current_input),
            "index": self._index,
            "run": self._run.model_dump(mode="json"),
        }

    @classmethod
    def from_state(
        cls,
        registry: Registry,
        store: RunStore,
        state: dict[str, Any],
    ) -> RunSession:
        """从落盘状态重建会话"""
        return cls(
            registry,
            store,
            FlowSpec.model_validate(state["flow"]),
            run=RunResult.model_validate(state["run"]),
            request=state.get("request"),
            runtime_vars=state.get("runtime_vars") or {},
            step_outputs=state.get("step_outputs") or {},
            current_input=state.get("current_input"),
            index=int(state.get("index", 0)),
        )

    def _finalize(self, *, status: str, error: str | None = None) -> None:
        """统一收尾:状态/结束时间/耗时落库,随后执行 hooks"""
        finished_at = _utc_now()
        self._run.status = status
        self._run.finished_at = finished_at
        self._run.duration_ms = int(
            (finished_at - self._started_at).total_seconds() * 1000
        )
        self._run.error = error
        self._finished = True
        self._store.save_run(self._run)
        self._execute_hooks(status)

    def _execute_hooks(self, status: str) -> None:
        if not self._flow.hooks:
            return
        hook_results = self._run_hooks(self._flow.hooks, status)
        if hook_results:
            self._run.hook_results = hook_results
            self._store.save_run(self._run)

    def _template_context(self) -> dict[str, Any]:
        """统一模板解析上下文构造"""
        return {
            "steps": self._step_outputs,
            "vars": self._runtime_vars,
            "input": self._current_input,
        }

    def _invoke_action(
        self,
        *,
        action_type: str,
        params: dict[str, Any],
        step_id: str,
    ) -> Any:
        """统一 action 调用:模板解析 + 查表 + 构造上下文 + 执行"""
        resolved_params = resolve_templates(params, self._template_context())
        handler = self._registry.get_action(action_type)
        return handler(
            ActionContext(
                run_id=self._run.run_id,
                step_id=step_id,
                input=self._current_input,
                vars=self._runtime_vars,
                artifacts_dir=self.run_artifacts_dir,
            ),
            resolved_params,
        )

    def _run_hooks(self, hooks: HookSpec, status: str) -> list[HookResult]:
        """执行 flow hooks 并记录每次结果(失败不影响主流程状态)"""
        hook_actions: list[ActionSpec] = []
        phase: HookPhase = "on_success" if status == "success" else "on_failure"
        if status == "success" and hooks.on_success:
            hook_actions = hooks.on_success
        elif status == "failed" and hooks.on_failure:
            hook_actions = hooks.on_failure

        results: list[HookResult] = []
        for index, hook_action in enumerate(hook_actions):
            hook_started = _utc_now()
            output: Any | None = None
            error: str | None = None
            try:
                output = to_jsonable(
                    self._invoke_action(
                        action_type=hook_action.type,
                        params=hook_action.params,
                        step_id="__hook__",
                    )
                )
                output = externalize_if_large(
                    output,
                    artifacts_dir=self.run_artifacts_dir,
                    file_stem=f"hook.{phase}.{index}.output",
                )
            except Exception as e:
                # hook 执行失败不影响主流程状态
                error = str(e)
                logger.warning(f"Hook {hook_action.type} failed: {e}")
            hook_finished = _utc_now()
            results.append(
                HookResult(
                    hook=phase,
                    action_type=hook_action.type,
                    status="failed" if error else "success",
                    started_at=hook_started,
                    finished_at=hook_finished,
                    duration_ms=int(
                        (hook_finished - hook_started).total_seconds() * 1000
                    ),
                    output=output,
                    error=error,
                )
            )
        return results

    def _execute_once(
        self,
        *,
        step: StepSpec,
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
                output = self._invoke_action(
                    action_type=step.action.type,
                    params=step.action.params,
                    step_id=step.id,
                )
                if step.check is not None:
                    check = self._registry.get_check(step.check.type)
                    check_passed = check(
                        CheckContext(
                            run_id=self._run.run_id,
                            step_id=step.id,
                            action_output=output,
                            vars=self._runtime_vars,
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
        step: StepSpec,
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
            loop_list = resolve_templates(step.for_each, self._template_context())
            if not isinstance(loop_list, list):
                loop_list = [loop_list]

            for item in loop_list:
                self._runtime_vars[step.for_item_var] = item

                iter_started = _utc_now()
                iter_output, iter_check_passed, iter_error = self._execute_once(
                    step=step
                )
                iter_finished = _utc_now()

                runtime_vars_clean = {
                    k: v
                    for k, v in self._runtime_vars.items()
                    if k != step.for_item_var
                }

                iterations.append(
                    {
                        "item": item,
                        "output": safe_deep_copy(iter_output),
                        "error": iter_error,
                        "check_passed": iter_check_passed,
                        "duration_ms": int(
                            (iter_finished - iter_started).total_seconds() * 1000
                        ),
                        "vars_snapshot": safe_deep_copy(runtime_vars_clean),
                    }
                )

                action_output = iter_output
                if iter_check_passed is not None:
                    check_passed = iter_check_passed
                if iter_error is not None:
                    step_error = f"Iteration error for item '{item}': {iter_error}"
                    break
        else:
            action_output, check_passed, step_error = self._execute_once(step=step)

        success = step_error is None
        if step.for_each is not None:
            self._runtime_vars.pop(step.for_item_var, None)
        return iterations, action_output, check_passed, success, step_error

    def _make_step_result(
        self,
        *,
        step_id: str,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        action_output: Any,
        check_passed: bool | None,
        error: str | None,
        iterations: list[dict] | None = None,
    ) -> StepResult:
        """统一 StepResult 构造"""
        return StepResult(
            step_id=step_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            action_output=action_output,
            check_passed=check_passed,
            error=error,
            iterations=iterations,
        )
