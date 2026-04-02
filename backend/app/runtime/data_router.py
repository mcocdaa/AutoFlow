# @file /backend/app/runtime/data_router.py
# @brief DAG工作流引擎 - 数据路由（数据路由、分发、条件评估）
# @create 2026-04-01 00:00:00

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.runtime.dag_models import (
    BaseNode,
    DAGWorkflow,
    Edge,
    Message,
    MessageMetadata,
    OutputPort,
)
from app.runtime.execution_state import ExecutionState


class _Namespace:
    def __init__(self, data: Dict[str, Any]):
        self.__dict__.update(data)


class ConditionEvaluator:
    @staticmethod
    def evaluate(
        condition: Optional[str], data: Any, variables: Dict[str, Any]
    ) -> bool:
        if condition is None:
            return True

        try:
            locals_dict = {
                "data": data,
                "variables": _Namespace(variables),
                "True": True,
                "False": False,
                "None": None,
            }

            result = eval(condition, {"__builtins__": {}}, locals_dict)
            return bool(result)
        except Exception:
            return False


class DataRouter:
    def __init__(self, workflow: DAGWorkflow, state: ExecutionState) -> None:
        self.workflow = workflow
        self.state = state
        self.condition_evaluator = ConditionEvaluator()

    def create_message(
        self,
        success: bool,
        data: Any,
        error: Optional[str],
        source_node_id: str,
        source_port_id: str,
    ) -> Message:
        metadata = MessageMetadata(
            timestamp=datetime.now().isoformat(),
            source_node=source_node_id,
            source_port=source_port_id,
        )
        return Message(
            success=success,
            data=data,
            error=error,
            metadata=metadata,
        )

    def distribute_outputs(
        self,
        node: BaseNode,
        outputs: Dict[str, Any],
    ) -> None:
        for output_port in node.outputs:
            if output_port.id in outputs:
                self._distribute_from_port(
                    node,
                    output_port,
                    outputs[output_port.id],
                )

        error_port = node.error_port
        record = self.state.history.get_record(node.id)
        if record.status == "failed" and record.error:
            self._distribute_from_port(
                node,
                error_port,
                record.error,
                is_error=True,
            )

    def _distribute_from_port(
        self,
        node: BaseNode,
        output_port: OutputPort,
        data: Any,
        is_error: bool = False,
    ) -> None:
        condition_passed = self.condition_evaluator.evaluate(
            output_port.condition,
            data,
            self.state.variables.all(),
        )

        if not condition_passed:
            return

        for edge in self.workflow.edges:
            if edge.source == f"{node.id}.{output_port.id}":
                self._send_to_edge(edge, data, is_error)

    def _send_to_edge(
        self,
        edge: Edge,
        data: Any,
        is_error: bool = False,
    ) -> None:
        target_node_id, target_port_id = edge.target.split(".")
        port_key = f"{target_node_id}.{target_port_id}"

        if is_error:
            message = self.create_message(
                success=False,
                data=None,
                error=str(data),
                source_node_id=edge.source.split(".")[0],
                source_port_id=edge.source.split(".")[1],
            )
        else:
            message = self.create_message(
                success=True,
                data=data,
                error=None,
                source_node_id=edge.source.split(".")[0],
                source_port_id=edge.source.split(".")[1],
            )

        self.state.available_inputs[port_key] = data

    def get_available_inputs_for_node(self, node: BaseNode) -> Dict[str, Any]:
        inputs = {}
        for port in node.inputs:
            port_key = f"{node.id}.{port.id}"
            if port_key in self.state.available_inputs:
                inputs[port.id] = self.state.available_inputs[port_key]
            elif port.default is not None:
                inputs[port.id] = port.default
        return inputs

    def has_required_inputs(self, node: BaseNode) -> bool:
        required_ports = [p for p in node.inputs if p.required]
        for port in required_ports:
            port_key = f"{node.id}.{port.id}"
            if port_key not in self.state.available_inputs:
                return False
        return True
