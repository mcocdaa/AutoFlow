# @file /backend/app/runtime/executor.py
# @brief DAG工作流引擎 - 节点执行器（状态管理、输入收集、重试逻辑、错误处理、输出分发）
# @create 2026-04-01 00:00:00

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.core.registry import ActionContext, Registry
from app.runtime.actions import ActionRegistry, get_action_registry
from app.runtime.dag_models import BaseNode
from app.runtime.execution_state import ExecutionState, NodeExecutionRecord, NodeStatus


class NodeExecutor:
    def __init__(
        self,
        state: ExecutionState,
        action_registry: Optional[ActionRegistry] = None,
        core_registry: Optional[Registry] = None,
        run_id: Optional[str] = None,
        artifacts_dir: Optional[Path] = None,
    ) -> None:
        self.state = state
        self.action_registry = action_registry or get_action_registry()
        self.core_registry = core_registry
        self.run_id = run_id or "default"
        self.artifacts_dir = artifacts_dir or Path("/tmp")

    def collect_inputs(self, node: BaseNode) -> Dict[str, Any]:
        inputs = {}
        if node.type == "start":
            for port in node.outputs:
                port_key = f"{node.id}.{port.id}"
                if port_key in self.state.available_inputs:
                    inputs[port.id] = self.state.available_inputs[port_key]
                elif port.default is not None:
                    inputs[port.id] = port.default
        else:
            for port in node.inputs:
                port_key = f"{node.id}.{port.id}"
                if port_key in self.state.available_inputs:
                    inputs[port.id] = self.state.available_inputs[port_key]
                elif port.default is not None:
                    inputs[port.id] = port.default
        return inputs

    def execute_node(self, node: BaseNode) -> Dict[str, Any]:
        record = self.state.history.get_record(node.id)
        record.start()

        inputs = self.collect_inputs(node)
        record.inputs = inputs

        max_attempts = node.retry.attempts + 1
        backoff_seconds = node.retry.backoff_seconds

        last_error = None

        for attempt in range(max_attempts):
            try:
                record.retry_count = attempt
                outputs = self._execute_node_logic(node, inputs)
                record.complete(outputs)
                return outputs
            except Exception as e:
                last_error = str(e)
                self.state.history.add_log(
                    f"Node {node.id} attempt {attempt + 1} failed: {last_error}"
                )

                if attempt < max_attempts - 1:
                    if backoff_seconds > 0:
                        time.sleep(backoff_seconds)

        record.fail(last_error or "Unknown error")
        raise Exception(last_error)

    def _execute_node_logic(
        self, node: BaseNode, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        if node.type == "start":
            return node.execute(inputs)
        elif node.type == "end":
            return node.execute(inputs)
        elif node.type == "pass":
            return node.execute(inputs)
        elif node.type == "action":
            action_type = node.config.get("action_type", "")
            if not action_type:
                raise ValueError("Action type not specified")

            try:
                handler = self.action_registry.get(action_type)
            except ValueError:
                if self.core_registry:
                    try:
                        core_handler = self.core_registry.get_action(action_type)
                        ctx = ActionContext(
                            run_id=self.run_id,
                            step_id=node.id,
                            input=inputs,
                            vars=self.state.variables.all(),
                            artifacts_dir=self.artifacts_dir,
                        )
                        result = core_handler(ctx, node.config)
                        if len(node.outputs) == 1:
                            return {node.outputs[0].id: result}
                        elif isinstance(result, dict):
                            return result
                        return {}
                    except KeyError:
                        pass
                raise ValueError(f"Action type '{action_type}' not found")

            ctx = ActionContext(
                run_id=self.run_id,
                step_id=node.id,
                input=inputs,
                vars=self.state.variables.all(),
                artifacts_dir=self.artifacts_dir,
            )
            return node.execute(
                inputs,
                action_handler=handler,
                ctx=ctx,
                config={**node.config, **inputs},
            )
        elif node.type == "input":
            inputs["__ext__"] = self.state.available_inputs.get(f"{node.id}.__ext__")
            return node.execute(inputs)
        else:
            raise ValueError(f"Unknown node type: {node.type}")

    def _execute_action_node(
        self, node: BaseNode, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        action_type = node.config.get("action_type", "")
        if not action_type:
            raise ValueError("Action type not specified")

        try:
            handler = self.action_registry.get(action_type)
        except ValueError:
            if self.core_registry:
                try:
                    core_handler = self.core_registry.get_action(action_type)
                    ctx = ActionContext(
                        run_id=self.run_id,
                        step_id=node.id,
                        input=inputs,
                        vars=self.state.variables.all(),
                        artifacts_dir=self.artifacts_dir,
                    )
                    result = core_handler(ctx, node.config)
                    if len(node.outputs) == 1:
                        return {node.outputs[0].id: result}
                    elif isinstance(result, dict):
                        return result
                    return {}
                except KeyError:
                    pass
            raise ValueError(f"Action type '{action_type}' not found")

        ctx = ActionContext(
            run_id=self.run_id,
            step_id=node.id,
            input=inputs,
            vars=self.state.variables.all(),
            artifacts_dir=self.artifacts_dir,
        )

        result = handler(ctx, {**node.config, **inputs})

        if len(node.outputs) == 1:
            return {node.outputs[0].id: result}
        elif isinstance(result, dict):
            return result
        return {}

    def mark_node_skipped(self, node: BaseNode) -> None:
        record = self.state.history.get_record(node.id)
        record.skip()

    def before_execute(self, node: BaseNode) -> None:
        self.state.history.add_log(f"Starting execution of node: {node.id}")

    def after_execute(self, node: BaseNode, outputs: Dict[str, Any]) -> None:
        self.state.history.add_log(f"Completed execution of node: {node.id}")

    def on_error(self, node: BaseNode, error: str) -> None:
        self.state.history.add_log(f"Error in node {node.id}: {error}")
