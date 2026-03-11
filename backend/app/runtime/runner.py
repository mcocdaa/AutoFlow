# @file /backend/app/runtime/runner.py
# @brief 最小 Runner：按顺序执行 Flow 的 steps
# @create 2026-02-21 00:00:00

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.runtime.models import FlowSpec, RunResult, StepResult
from app.runtime.output_externalizer import externalize_if_large
from app.runtime.registry import ActionContext, CheckContext, Registry
from app.runtime.store import RunStore


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
        for step in flow.steps:
            step_started = _utc_now()
            step_error: str | None = None
            action_output: Any | None = None
            check_passed: bool | None = None

            attempts = step.retry.attempts if step.retry else 0
            backoff = step.retry.backoff_seconds if step.retry else 0.0

            for attempt in range(max(1, attempts + 1)):
                try:
                    action = self._registry.get_action(step.action.type)
                    action_output = action(
                        ActionContext(
                            run_id=run_id,
                            step_id=step.id,
                            input=current_input,
                            vars=runtime_vars,
                            artifacts_dir=run_artifacts_dir,
                        ),
                        step.action.params,
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

            current_input = action_output

        finished_at = _utc_now()
        run.status = "success"
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        self._store.save_run(run)
        return run
