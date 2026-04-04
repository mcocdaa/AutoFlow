# @file /backend/app/runtime/workflow_runner.py
# @brief DAG工作流引擎 - 工作流运行器（整合调度器和执行器、工作流执行流程）
# @create 2026-04-01 00:00:00

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from app.core.registry import Registry
from app.runtime.actions import ActionRegistry, get_action_registry
from app.runtime.dag_models import DAGWorkflow
from app.runtime.data_router import DataRouter
from app.runtime.execution_state import ExecutionState, NodeStatus, WorkflowStatus
from app.runtime.executor import NodeExecutor
from app.runtime.scheduler import DAGScheduler


class WaitingForInputError(Exception):
    """到达 InputNode 但尚无外部数据注入时抛出"""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Waiting for input on node: {node_id}")


class WorkflowRunner:
    def __init__(
        self,
        workflow: DAGWorkflow,
        action_registry: Optional[ActionRegistry] = None,
        core_registry: Optional[Registry] = None,
        run_id: Optional[str] = None,
        artifacts_dir: Optional[Path] = None,
    ) -> None:
        self.workflow = workflow
        self.state = ExecutionState()
        self.action_registry = action_registry or get_action_registry()
        self.core_registry = core_registry
        self.run_id = run_id or "default"
        self.artifacts_dir = artifacts_dir or Path("/tmp")

        self.scheduler = DAGScheduler(workflow, self.state)
        self.executor = NodeExecutor(
            state=self.state,
            action_registry=self.action_registry,
            core_registry=self.core_registry,
            run_id=self.run_id,
            artifacts_dir=self.artifacts_dir,
        )
        self.data_router = DataRouter(workflow, self.state)

    # ── Public API ──────────────────────────────────────────────────────────

    def run(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        inputs = inputs or {}
        self._initialize_workflow(inputs)
        self.state.workflow_status = WorkflowStatus.RUNNING

        try:
            self._run_loop()
            self._finalize_workflow()
            return self._get_workflow_output()
        except WaitingForInputError as e:
            self.state.workflow_status = WorkflowStatus.WAITING
            self.state.waiting_node_id = e.node_id
            return {"status": "waiting", "waiting_node_id": e.node_id}
        except Exception as e:
            self.state.workflow_status = WorkflowStatus.FAILED
            self.state.history.add_log(f"Workflow failed: {str(e)}")
            raise

    def resume(self) -> Dict[str, Any]:
        """继续执行（外部输入已注入 state.available_inputs）"""
        self.state.workflow_status = WorkflowStatus.RUNNING
        self.state.waiting_node_id = None

        try:
            self._run_loop()
            self._finalize_workflow()
            return self._get_workflow_output()
        except WaitingForInputError as e:
            self.state.workflow_status = WorkflowStatus.WAITING
            self.state.waiting_node_id = e.node_id
            return {"status": "waiting", "waiting_node_id": e.node_id}
        except Exception as e:
            self.state.workflow_status = WorkflowStatus.FAILED
            self.state.history.add_log(f"Workflow failed on resume: {str(e)}")
            raise

    def serialize_state(self) -> Dict[str, Any]:
        """序列化当前执行状态，用于持久化到数据库"""
        return {
            "available_inputs": self.state.available_inputs,
            "history": {
                node_id: {
                    "status": rec.status,
                    "inputs": rec.inputs,
                    "outputs": rec.outputs,
                    "retry_count": rec.retry_count,
                }
                for node_id, rec in self.state.history.records.items()
            },
            "waiting_node_id": self.state.waiting_node_id,
        }

    def restore_state(self, state_data: Dict[str, Any]) -> None:
        """从序列化数据恢复执行状态，并重建调度器"""
        self.state.available_inputs = dict(state_data.get("available_inputs", {}))
        self.state.waiting_node_id = state_data.get("waiting_node_id")

        for node_id, rec_data in state_data.get("history", {}).items():
            rec = self.state.history.get_record(node_id)
            rec.status = NodeStatus(rec_data["status"])
            rec.inputs = rec_data.get("inputs", {})
            rec.outputs = rec_data.get("outputs", {})
            rec.retry_count = rec_data.get("retry_count", 0)

        # 根据已恢复的历史重建调度器（仅 PENDING 节点会进入就绪队列）
        self.scheduler = DAGScheduler(self.workflow, self.state)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        while not self.scheduler.is_all_nodes_processed():
            node_id = self.scheduler.get_ready_node()
            if node_id is None:
                if self.scheduler.has_ready_nodes():
                    continue
                break
            self._process_node(node_id)

    def _initialize_workflow(self, inputs: Dict[str, Any]) -> None:
        self.state.reset()
        self.scheduler.reset()
        self.state.workflow_status = WorkflowStatus.IDLE

        for node_id, node in self.workflow.nodes.items():
            if node.type == "start":
                for port in node.outputs:
                    port_key = f"{node_id}.{port.id}"
                    if port.id in inputs:
                        self.state.available_inputs[port_key] = inputs[port.id]
                    elif port.default is not None:
                        self.state.available_inputs[port_key] = port.default

        self.state.history.add_log("Workflow initialized")

    def _process_node(self, node_id: str) -> None:
        node = self.workflow.nodes[node_id]

        if node.type == "input":
            ext_key = f"{node_id}.__ext__"
            if ext_key not in self.state.available_inputs:
                raise WaitingForInputError(node_id)

        self.executor.before_execute(node)
        try:
            outputs = self.executor.execute_node(node)
            self.executor.after_execute(node, outputs)
            self.data_router.distribute_outputs(node, outputs)
            self.scheduler.mark_node_completed(node_id)
        except WaitingForInputError:
            raise
        except Exception as e:
            self.executor.on_error(node, str(e))
            self.data_router.distribute_outputs(node, {})
            raise

    def _finalize_workflow(self) -> None:
        all_completed = True
        has_failed = False

        for node_id in self.workflow.nodes:
            record = self.state.history.get_record(node_id)
            if record.status == "failed":
                has_failed = True
            elif record.status in ["pending", "running"]:
                all_completed = False

        if has_failed:
            self.state.workflow_status = WorkflowStatus.FAILED
        elif all_completed:
            self.state.workflow_status = WorkflowStatus.COMPLETED
        else:
            self.state.workflow_status = WorkflowStatus.STOPPED

        self.state.history.add_log(
            f"Workflow finalized with status: {self.state.workflow_status}"
        )

    def _get_workflow_output(self) -> Dict[str, Any]:
        output = {}
        for node_id, node in self.workflow.nodes.items():
            if node.type == "end":
                record = self.state.history.get_record(node_id)
                output.update(record.outputs)
        return output

    def get_execution_history(self) -> Dict[str, Any]:
        return {
            "status": self.state.workflow_status,
            "records": {
                node_id: {
                    "status": record.status,
                    "start_time": (
                        record.start_time.isoformat() if record.start_time else None
                    ),
                    "end_time": (
                        record.end_time.isoformat() if record.end_time else None
                    ),
                    "error": record.error,
                    "inputs": record.inputs,
                    "outputs": record.outputs,
                    "retry_count": record.retry_count,
                }
                for node_id, record in self.state.history.records.items()
            },
            "logs": self.state.history.logs,
        }
