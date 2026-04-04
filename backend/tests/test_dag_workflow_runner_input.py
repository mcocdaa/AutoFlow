# @file /backend/tests/test_dag_workflow_runner_input.py
# @brief TDD tests for WorkflowRunner pause/resume with InputNode

from __future__ import annotations

import pytest

from app.runtime.dag_models import DAGWorkflow, Edge, InputPort, OutputPort, RetrySpec
from app.runtime.execution_state import NodeStatus, WorkflowStatus
from app.runtime.nodes import EndNode, InputNode, StartNode
from app.runtime.workflow_runner import WaitingForInputError, WorkflowRunner


def _retry() -> RetrySpec:
    return RetrySpec(attempts=0, backoff_seconds=0.0)


def make_start_input_end_workflow() -> DAGWorkflow:
    """
    start (standalone, no outputs) + input_1 → end

    Both start and input_1 are in_degree=0 so both enter ready queue.
    start executes first (insertion order), then runner hits input_1 and pauses.
    """
    start = StartNode(id="start", retry=_retry(), config={}, metadata={}, outputs=[])
    inp = InputNode(
        id="input_1", name="User Input", retry=_retry(), config={}, metadata={}
    )
    end = EndNode(
        id="end",
        retry=_retry(),
        config={},
        metadata={},
        inputs=[InputPort(id="result", name="Result", type="any", required=True)],
    )
    return DAGWorkflow(
        name="Input Test",
        nodes={"start": start, "input_1": inp, "end": end},
        edges=[
            Edge(id="e1", source="input_1.output", target="end.result"),
        ],
    )


def make_two_input_workflow() -> DAGWorkflow:
    """
    start + input_1 → input_2 → end

    input_1 has no required inputs (in_degree=0) and is reached first.
    After submitting to input_1, input_2 becomes ready; it also pauses.
    """
    start = StartNode(id="start", retry=_retry(), config={}, metadata={}, outputs=[])
    inp1 = InputNode(id="input_1", retry=_retry(), config={}, metadata={})
    inp2 = InputNode(id="input_2", retry=_retry(), config={}, metadata={})
    end = EndNode(
        id="end",
        retry=_retry(),
        config={},
        metadata={},
        inputs=[InputPort(id="result", name="Result", type="any", required=True)],
    )
    return DAGWorkflow(
        name="Two Input Test",
        nodes={"start": start, "input_1": inp1, "input_2": inp2, "end": end},
        edges=[
            Edge(id="e1", source="input_1.output", target="input_2.output"),
            Edge(id="e2", source="input_2.output", target="end.result"),
        ],
    )


# ── Tests ────────────────────────────────────────────────────────────────────


def test_waiting_for_input_error_carries_node_id():
    err = WaitingForInputError("node_xyz")
    assert err.node_id == "node_xyz"
    assert "node_xyz" in str(err)


def test_runner_pauses_at_input_node():
    workflow = make_start_input_end_workflow()
    runner = WorkflowRunner(workflow)
    result = runner.run()

    assert result.get("status") == "waiting"
    assert result.get("waiting_node_id") == "input_1"
    assert runner.state.workflow_status == WorkflowStatus.WAITING
    assert runner.state.waiting_node_id == "input_1"


def test_runner_serialize_state_contains_required_keys():
    workflow = make_start_input_end_workflow()
    runner = WorkflowRunner(workflow)
    runner.run()

    serialized = runner.serialize_state()
    assert "available_inputs" in serialized
    assert "history" in serialized
    assert "waiting_node_id" in serialized
    assert serialized["waiting_node_id"] == "input_1"
    # start should appear in history as completed
    assert "start" in serialized["history"]
    assert serialized["history"]["start"]["status"] == NodeStatus.COMPLETED


def test_runner_restore_and_resume():
    """Full cycle: run -> pause -> inject input -> resume -> complete."""
    workflow = make_start_input_end_workflow()

    runner1 = WorkflowRunner(workflow)
    result1 = runner1.run()
    assert result1["status"] == "waiting"

    state_data = runner1.serialize_state()

    runner2 = WorkflowRunner(workflow)
    runner2.restore_state(state_data)
    runner2.state.available_inputs["input_1.__ext__"] = "my answer"

    result2 = runner2.resume()

    assert result2.get("status") != "waiting"
    assert runner2.state.workflow_status == WorkflowStatus.COMPLETED


def test_runner_resume_delivers_data_to_end():
    workflow = make_start_input_end_workflow()

    runner1 = WorkflowRunner(workflow)
    runner1.run()
    state_data = runner1.serialize_state()

    runner2 = WorkflowRunner(workflow)
    runner2.restore_state(state_data)
    runner2.state.available_inputs["input_1.__ext__"] = "hello"

    result2 = runner2.resume()
    assert result2.get("result") == "hello"
