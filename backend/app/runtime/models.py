# @file /backend/app/runtime/models.py
# @brief Flow/Step/Action/Check 与执行结果的 Pydantic 模型
# @create 2026-02-21 00:00:00
# @update 2026-03-30 添加 WorkflowSpec SQLAlchemy 模型和相关 Pydantic 模型

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database_manager import database_manager

Base = database_manager.Base


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
OldRunStatus = Literal["success", "failed", "running"]


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
    status: OldRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    steps: list[StepResult] = Field(default_factory=list)
    error: str | None = None


class WorkflowSpec(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    nodes = Column(JSON, nullable=False)
    edges = Column(JSON, nullable=False)
    yaml = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkflowSaveRequest(_Base):
    name: str
    description: Optional[str] = None
    nodes: List[dict] = Field(default_factory=list)
    edges: List[dict] = Field(default_factory=list)
    yaml: str


class WorkflowResponse(_Base):
    id: str
    name: str
    description: Optional[str] = None
    nodes: List[dict]
    edges: List[dict]
    yaml: str
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(_Base):
    workflows: List[WorkflowResponse]


class NodeState(_Base):
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: Any = None


class RunSpec(Base):
    __tablename__ = "runs"

    id = Column(String(64), primary_key=True, index=True)
    workflow_id = Column(String(64), index=True, nullable=False)
    status = Column(String(32), nullable=False, default=RunStatus.PENDING.value)
    inputs = Column(JSON, nullable=False)
    node_states = Column(JSON, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)


class V2WorkflowCreateRequest(_Base):
    name: str
    description: Optional[str] = None
    yaml: str


class V2WorkflowUpdateRequest(_Base):
    name: Optional[str] = None
    description: Optional[str] = None
    yaml: Optional[str] = None


class V2WorkflowResponse(_Base):
    id: str
    name: str
    description: Optional[str] = None
    yaml: str
    created_at: datetime
    updated_at: datetime


class V2WorkflowListItem(_Base):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class V2WorkflowListResponse(_Base):
    workflows: List[V2WorkflowListItem]
    total: int
    page: int
    page_size: int


class V2RunTriggerRequest(_Base):
    inputs: Dict[str, Any] = Field(default_factory=dict)


class V2RunResponse(_Base):
    run_id: str
    workflow_id: str
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    node_states: Dict[str, NodeState] = Field(default_factory=dict)
    error: Optional[str] = None


class V2RunListItem(_Base):
    run_id: str
    workflow_id: str
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class V2RunListResponse(_Base):
    runs: List[V2RunListItem]
    total: int
    page: int
    page_size: int


class V2SuccessResponse(_Base):
    success: bool = True
