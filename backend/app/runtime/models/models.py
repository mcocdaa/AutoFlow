# @file /backend/app/runtime/models/models.py
# @brief Flow/Step/Action/Check 与执行结果的 Pydantic 模型
# @create 2026-02-21 00:00:00

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class _Base(BaseModel):
    model_config = {"extra": "forbid"}


class ActionSpec(_Base):
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class CheckSpec(_Base):
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class RetrySpec(_Base):
    attempts: int = 0
    backoff_seconds: float = 0.0


class StepSpec(_Base):
    id: str
    name: str | None = None
    action: ActionSpec
    check: CheckSpec | None = None
    retry: RetrySpec | None = None
    output_var: str | None = None
    for_each: str | None = None
    for_item_var: str = "item"
    condition: str | None = None


class HookSpec(_Base):
    on_success: list[ActionSpec] | None = None
    on_failure: list[ActionSpec] | None = None


class FlowSpec(_Base):
    version: str
    name: str
    steps: list[StepSpec]
    hooks: HookSpec | None = None


StepStatus = Literal["success", "failed", "skipped"]
RunStatus = Literal["success", "failed", "running"]


class StepResult(_Base):
    step_id: str
    status: StepStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    action_output: Any | None = None
    check_passed: bool | None = None
    error: str | None = None
    iterations: list[dict] | None = None


class RunResult(_Base):
    run_id: str
    flow_name: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    steps: list[StepResult] = Field(default_factory=list)
    error: str | None = None
