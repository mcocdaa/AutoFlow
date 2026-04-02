# @file /backend/app/runtime/execution_state.py
# @brief DAG工作流引擎 - 执行状态管理（状态枚举、执行历史、变量作用域）
# @create 2026-04-01 00:00:00

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeExecutionRecord:
    def __init__(
        self,
        node_id: str,
        status: NodeStatus = NodeStatus.PENDING,
    ) -> None:
        self.node_id = node_id
        self.status = status
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.retry_count: int = 0

    def start(self) -> None:
        self.status = NodeStatus.RUNNING
        self.start_time = datetime.now()

    def complete(self, outputs: Dict[str, Any]) -> None:
        self.status = NodeStatus.COMPLETED
        self.end_time = datetime.now()
        self.outputs = outputs

    def fail(self, error: str) -> None:
        self.status = NodeStatus.FAILED
        self.end_time = datetime.now()
        self.error = error

    def skip(self) -> None:
        self.status = NodeStatus.SKIPPED
        self.end_time = datetime.now()


class ExecutionHistory:
    def __init__(self) -> None:
        self.records: Dict[str, NodeExecutionRecord] = {}
        self.logs: List[str] = []

    def get_record(self, node_id: str) -> NodeExecutionRecord:
        if node_id not in self.records:
            self.records[node_id] = NodeExecutionRecord(node_id)
        return self.records[node_id]

    def add_log(self, message: str) -> None:
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")


class VariableScope:
    def __init__(self, parent: Optional[VariableScope] = None) -> None:
        self.parent = parent
        self.variables: Dict[str, Any] = {}

    def get(self, name: str, default: Any = None) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name, default)
        return default

    def set(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def set_local(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.has(name)
        return False

    def all(self) -> Dict[str, Any]:
        result = {}
        if self.parent:
            result.update(self.parent.all())
        result.update(self.variables)
        return result


class ExecutionState:
    def __init__(self) -> None:
        self.workflow_status: WorkflowStatus = WorkflowStatus.IDLE
        self.history = ExecutionHistory()
        self.variables = VariableScope()
        self.available_inputs: Dict[str, Any] = {}

    def reset(self) -> None:
        self.workflow_status = WorkflowStatus.IDLE
        self.history = ExecutionHistory()
        self.variables = VariableScope()
        self.available_inputs = {}
