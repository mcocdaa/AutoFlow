# @file /backend/app/runtime/session.py
# @brief 可暂停的 Flow 执行会话(支持线性执行与 DAG 拓扑并发执行)
# @create 2026-09-15
# @update 2026-09-20 支持 DAG 拓扑分层与并发执行，状态落盘与产物写入线程安全

from __future__ import annotations

import concurrent.futures
import copy
import logging
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry
from app.runtime.dag import (
    detect_cycles,
    resolve_execution_layers,
    validate_dependencies,
)
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

_DEFAULT = object()


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RunSession:
    """可暂停的执行会话

    整条执行(Runner.run_flow)与调试单步(Debug API)共用该类:
    - step(): 执行下一个待执行步骤(线性模式)或下一拓扑层(DAG 模式)
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
        layer_index: int = 0,
        max_workers: int | None = None,
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
        self._layer_index = layer_index
        self._started_at = run.started_at
        self._finished = run.status != "running"
        self._max_workers = max_workers
        self._lock = threading.RLock()

        # 判断是否为 DAG 模式
        self._is_dag = any(step.depends_on is not None for step in self._flow.steps)
        if self._is_dag:
            self._layers = resolve_execution_layers(self._flow.steps)
        else:
            self._layers = []

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
        max_workers: int | None = None,
    ) -> RunSession:
        """创建新会话:初始化 run 与产物目录"""
        if any(s.depends_on is not None for s in flow.steps):
            validate_dependencies(flow.steps)
            detect_cycles(flow.steps)

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
        if request is not None:
            store.save_request(run_id, request)
        return cls(
            registry,
            store,
            flow,
            run=run,
            request=request,
            runtime_vars=copy.deepcopy(dict(vars or {})),
            current_input=input,
            max_workers=max_workers,
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
                "depends_on": step.depends_on,
            }
            for step in self._flow.steps
        ]

    @classmethod
    def fork_from_run(
        cls,
        registry: Registry,
        store: RunStore,
        flow: FlowSpec,
        *,
        source_run: RunResult,
        request: dict[str, Any] | None,
        next_step_index: int,
        max_workers: int | None = None,
    ) -> RunSession:
        """从历史运行的第 next_step_index 步继续,按 session.step() 语义重建状态

        - next_step_index = k: 重试第 k 步;= k+1: 从第 k 步之后继续
        - 前缀步骤结果原样复制,lineage 写入 parent_run_id/fork_step_index
        """
        if next_step_index < 0 or next_step_index > len(source_run.steps):
            raise ValueError(
                f"next_step_index 超出范围: {next_step_index} "
                f"(0..{len(source_run.steps)})"
            )
        if next_step_index > len(flow.steps):
            raise ValueError(f"next_step_index 超出 Flow 步骤数: {next_step_index}")

        prefix = [copy.deepcopy(step) for step in source_run.steps[:next_step_index]]
        runtime_vars = copy.deepcopy(dict((request or {}).get("vars") or {}))
        step_outputs: dict[str, Any] = {}
        current_input = (request or {}).get("input")
        for index, result in enumerate(prefix):
            if result.status != "success":
                continue
            if result.action_output is not None:
                step_outputs[result.step_id] = result.action_output
            step_spec = next(
                (s for s in flow.steps if s.id == result.step_id),
                flow.steps[index] if index < len(flow.steps) else None,
            )
            if step_spec and step_spec.output_var is not None:
                runtime_vars[step_spec.output_var] = to_jsonable(result.action_output)
            current_input = result.action_output

        run_id = str(uuid.uuid4())
        (store.artifacts_dir / run_id).mkdir(parents=True, exist_ok=True)
        run = RunResult(
            run_id=run_id,
            flow_name=flow.name,
            status="running",
            started_at=_utc_now(),
            steps=prefix,
            parent_run_id=source_run.run_id,
            fork_step_index=next_step_index,
        )
        store.save_run(run)
        if request is not None:
            store.save_request(run_id, request)

        is_dag = any(s.depends_on is not None for s in flow.steps)
        layer_index = 0
        if is_dag:
            layers = resolve_execution_layers(flow.steps)
            completed_step_ids = {r.step_id for r in prefix if r.status == "success"}
            for idx, layer in enumerate(layers):
                if all(s.id in completed_step_ids for s in layer):
                    layer_index = idx + 1
                else:
                    break

        return cls(
            registry,
            store,
            flow,
            run=run,
            request=request,
            runtime_vars=runtime_vars,
            step_outputs=step_outputs,
            current_input=current_input,
            index=next_step_index,
            layer_index=layer_index,
            max_workers=max_workers,
        )

    def step(self) -> None:
        """执行下一个待执行步骤或待执行层(已结束则幂等返回)"""
        if self._finished:
            return
        if not self._is_dag:
            self._step_linear()
        else:
            self._step_dag_layer()

    def _step_linear(self) -> None:
        """线性执行模式(100% 保持既有逻辑向后兼容)"""
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
                with self._lock:
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
            with self._lock:
                action_output = externalize_if_large(
                    action_output,
                    artifacts_dir=self.run_artifacts_dir,
                    file_stem=f"{step.id}.action_output",
                )

        with self._lock:
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

    def _compute_step_input(self, step: StepSpec) -> Any:
        """根据前置依赖计算步骤输入"""
        if not step.depends_on:
            return self._current_input
        if len(step.depends_on) == 1:
            return self._step_outputs.get(step.depends_on[0])
        return {dep: self._step_outputs.get(dep) for dep in step.depends_on}

    def _execute_single_dag_step(self, step: StepSpec) -> tuple[StepSpec, StepResult]:
        """执行 DAG 单个步骤并返回结果"""
        step_started = _utc_now()
        step_input = self._compute_step_input(step)

        if step.condition is not None:
            resolved_condition = resolve_templates(
                step.condition,
                self._template_context(step_input),
            )
            if not evaluate_condition(str(resolved_condition)):
                step_finished = _utc_now()
                return step, self._make_step_result(
                    step_id=step.id,
                    status="skipped",
                    started_at=step_started,
                    finished_at=step_finished,
                    action_output=None,
                    check_passed=None,
                    error=None,
                )

        try:
            iterations, action_output, check_passed, success, step_error = (
                self._execute_step(step, step_input=step_input)
            )
        except Exception as exc:
            iterations, action_output, check_passed, success, step_error = (
                None,
                None,
                False,
                False,
                str(exc),
            )

        step_finished = _utc_now()
        if action_output is not None:
            with self._lock:
                action_output = externalize_if_large(
                    action_output,
                    artifacts_dir=self.run_artifacts_dir,
                    file_stem=f"{step.id}.action_output",
                )

        return step, self._make_step_result(
            step_id=step.id,
            status="success" if success else "failed",
            started_at=step_started,
            finished_at=step_finished,
            action_output=action_output,
            check_passed=check_passed,
            error=step_error,
            iterations=iterations,
        )

    def _execute_layer(
        self, layer: list[StepSpec]
    ) -> list[tuple[StepSpec, StepResult]]:
        """并发执行同一拓扑层的所有步骤(无相互依赖)"""
        if len(layer) == 1:
            return [self._execute_single_dag_step(layer[0])]

        max_workers = self._max_workers or min(len(layer), 16)
        results_map: dict[str, tuple[StepSpec, StepResult]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_step = {
                executor.submit(self._execute_single_dag_step, s): s for s in layer
            }
            for future in concurrent.futures.as_completed(future_to_step):
                s = future_to_step[future]
                try:
                    res = future.result()
                    results_map[s.id] = res
                except Exception as exc:
                    now = _utc_now()
                    failed_result = self._make_step_result(
                        step_id=s.id,
                        status="failed",
                        started_at=now,
                        finished_at=now,
                        action_output=None,
                        check_passed=False,
                        error=str(exc),
                    )
                    results_map[s.id] = (s, failed_result)

        return [results_map[s.id] for s in layer]

    def _step_dag_layer(self) -> None:
        """DAG 拓扑分层并发执行"""
        if self._layer_index >= len(self._layers):
            self._finalize(status="success")
            return

        current_layer = self._layers[self._layer_index]
        if not current_layer:
            self._layer_index += 1
            if self._layer_index >= len(self._layers):
                self._finalize(status="success")
            return

        layer_results = self._execute_layer(current_layer)

        with self._lock:
            layer_has_error = False
            first_error: str | None = None
            last_output: Any = None

            for step, res in layer_results:
                self._run.steps.append(res)
                if res.status == "failed":
                    layer_has_error = True
                    if first_error is None:
                        first_error = res.error
                elif res.status == "success":
                    self._step_outputs[step.id] = res.action_output
                    last_output = res.action_output
                    if step.output_var is not None:
                        self._runtime_vars[step.output_var] = to_jsonable(
                            res.action_output
                        )

            if len(layer_results) == 1:
                self._current_input = last_output
            else:
                self._current_input = {
                    s.id: r.action_output
                    for s, r in layer_results
                    if r.status == "success"
                }

            self._index += len(current_layer)
            self._layer_index += 1
            self._store.save_run(self._run)

            if layer_has_error:
                self._finalize(status="failed", error=first_error)
                return

            if self._layer_index >= len(self._layers):
                self._finalize(status="success")

    def run_to_completion(self) -> RunResult:
        """执行到底并触发 hooks,返回最终 run"""
        while not self._finished:
            self.step()
        return self._run

    def to_state(self) -> dict[str, Any]:
        """完整会话状态(JSON 可序列化),用于落盘/跨 worker 恢复"""
        with self._lock:
            return {
                "flow": self._flow.model_dump(mode="json"),
                "request": to_jsonable(self._request),
                "runtime_vars": to_jsonable(self._runtime_vars),
                "step_outputs": to_jsonable(self._step_outputs),
                "current_input": to_jsonable(self._current_input),
                "index": self._index,
                "layer_index": self._layer_index,
                "run": self._run.model_dump(mode="json"),
            }

    @classmethod
    def from_state(
        cls,
        registry: Registry,
        store: RunStore,
        state: dict[str, Any],
        *,
        max_workers: int | None = None,
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
            layer_index=int(state.get("layer_index", 0)),
            max_workers=max_workers,
        )

    def _finalize(self, *, status: str, error: str | None = None) -> None:
        """统一收尾:状态/结束时间/耗时落库,随后执行 hooks"""
        with self._lock:
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
            with self._lock:
                self._run.hook_results = hook_results
                self._store.save_run(self._run)

    def _template_context(
        self,
        step_input: Any = _DEFAULT,
        vars_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """统一模板解析上下文构造"""
        from app.core.secrets_vault import get_secrets_vault

        actual_input = self._current_input if step_input is _DEFAULT else step_input
        actual_vars = self._runtime_vars if vars_override is None else vars_override
        return {
            "steps": self._step_outputs,
            "vars": actual_vars,
            "input": actual_input,
            "secrets": get_secrets_vault().get_all_secrets(),
        }

    def _invoke_action(
        self,
        *,
        action_type: str,
        params: dict[str, Any],
        step_id: str,
        step_input: Any = _DEFAULT,
        vars_override: dict[str, Any] | None = None,
    ) -> Any:
        """统一 action 调用:模板解析 + 查表 + 构造上下文 + 执行"""
        actual_input = self._current_input if step_input is _DEFAULT else step_input
        actual_vars = self._runtime_vars if vars_override is None else vars_override
        resolved_params = resolve_templates(
            params, self._template_context(actual_input, actual_vars)
        )
        handler = self._registry.get_action(action_type)
        return handler(
            ActionContext(
                run_id=self._run.run_id,
                step_id=step_id,
                input=actual_input,
                vars=actual_vars,
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
        step_input: Any = _DEFAULT,
        vars_override: dict[str, Any] | None = None,
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
                    step_input=step_input,
                    vars_override=vars_override,
                )
                if step.check is not None:
                    check = self._registry.get_check(step.check.type)
                    actual_vars = (
                        self._runtime_vars if vars_override is None else vars_override
                    )
                    check_passed = check(
                        CheckContext(
                            run_id=self._run.run_id,
                            step_id=step.id,
                            action_output=output,
                            vars=actual_vars,
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
        step_input: Any = _DEFAULT,
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
                step.for_each, self._template_context(step_input)
            )
            if not isinstance(loop_list, list):
                loop_list = [loop_list]

            local_vars = dict(self._runtime_vars)
            for item in loop_list:
                local_vars[step.for_item_var] = item

                iter_started = _utc_now()
                iter_output, iter_check_passed, iter_error = self._execute_once(
                    step=step,
                    step_input=step_input,
                    vars_override=local_vars,
                )
                iter_finished = _utc_now()

                runtime_vars_clean = {
                    k: v for k, v in local_vars.items() if k != step.for_item_var
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
            action_output, check_passed, step_error = self._execute_once(
                step=step,
                step_input=step_input,
            )

        success = step_error is None
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
