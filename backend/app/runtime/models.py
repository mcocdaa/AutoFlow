# @file /backend/app/runtime/models.py
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
    output_var: str | None = None  # 如果设置，将 action_output 存入 runtime_vars[output_var]
    for_each: str | None = None  # 引用一个列表变量，如 "{{vars.items}}"
    for_item_var: str = "item"   # 循环变量名，默认 "item"
    condition: str | None = None  # 条件表达式，为 None 时始终执行


class FlowSpec(_Base):
    version: str
    name: str
    steps: list[StepSpec]


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
    iterations: list[dict] | None = None  # for 循环时记录每次迭代结果


class RunResult(_Base):
    run_id: str
    flow_name: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    steps: list[StepResult] = Field(default_factory=list)
    error: str | None = None

