# @file /backend/tests/test_api_v2_runs_input.py
# @brief TDD tests for InputNode API: trigger_run executes, submit_input resumes

from __future__ import annotations

import pytest

INPUT_WORKFLOW_YAML = """\
version: "2.0"
name: "input-test"
description: "start + input_node -> end"
inputs: {}
nodes:
  start:
    id: "start"
    name: "Start"
    type: "start"
    config: {}
    metadata: {x: 0, y: 0}
    inputs: []
    outputs: []
  inp:
    id: "inp"
    name: "User Input"
    type: "input"
    config: {}
    metadata: {x: 200, y: 0}
    inputs: []
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
    error_port:
      id: "error"
      name: "Error"
      type: "any"
  end:
    id: "end"
    name: "End"
    type: "end"
    config: {}
    metadata: {x: 400, y: 0}
    inputs:
      - id: "result"
        name: "Result"
        type: "any"
        required: true
    outputs: []
edges:
  - id: "e1"
    source: "inp.output"
    target: "end.result"
"""

SIMPLE_WORKFLOW_YAML = """\
version: "2.0"
name: "simple"
inputs: {}
nodes:
  start:
    id: "start"
    name: "Start"
    type: "start"
    config: {}
    metadata: {x: 0, y: 0}
    inputs: []
    outputs:
      - id: "msg"
        name: "Msg"
        type: "string"
  end:
    id: "end"
    name: "End"
    type: "end"
    config: {}
    metadata: {x: 200, y: 0}
    inputs:
      - id: "result"
        name: "Result"
        type: "string"
        required: true
    outputs: []
edges:
  - id: "e1"
    source: "start.msg"
    target: "end.result"
"""


def _create_workflow(client, yaml_str: str, name: str = "Test") -> str:
    resp = client.post(
        "/v2/workflows",
        json={"name": name, "yaml": yaml_str},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


class TestTriggerRunExecutes:
    def test_simple_workflow_completes(self, client):
        wf_id = _create_workflow(client, SIMPLE_WORKFLOW_YAML, "simple")
        resp = client.post(
            f"/v2/workflows/{wf_id}/runs", json={"inputs": {"msg": "hi"}}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["waiting_node_id"] is None

    def test_input_workflow_pauses(self, client):
        wf_id = _create_workflow(client, INPUT_WORKFLOW_YAML, "with-input")
        resp = client.post(f"/v2/workflows/{wf_id}/runs", json={"inputs": {}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused"
        assert data["waiting_node_id"] == "inp"


class TestSubmitInput:
    def test_submit_input_resumes_and_completes(self, client):
        wf_id = _create_workflow(client, INPUT_WORKFLOW_YAML, "with-input-2")
        run_resp = client.post(f"/v2/workflows/{wf_id}/runs", json={"inputs": {}})
        run_id = run_resp.json()["run_id"]
        assert run_resp.json()["status"] == "paused"

        submit_resp = client.post(
            f"/v2/runs/{run_id}/nodes/inp/input",
            json={"data": "hello from user"},
        )
        assert submit_resp.status_code == 200
        data = submit_resp.json()
        assert data["status"] == "completed"
        assert data["waiting_node_id"] is None

    def test_submit_input_to_non_paused_run_returns_400(self, client):
        wf_id = _create_workflow(client, SIMPLE_WORKFLOW_YAML, "simple-2")
        run_resp = client.post(
            f"/v2/workflows/{wf_id}/runs", json={"inputs": {"msg": "x"}}
        )
        run_id = run_resp.json()["run_id"]
        assert run_resp.json()["status"] == "completed"

        resp = client.post(
            f"/v2/runs/{run_id}/nodes/start/input",
            json={"data": "irrelevant"},
        )
        assert resp.status_code == 400

    def test_submit_input_to_unknown_run_returns_404(self, client):
        resp = client.post(
            "/v2/runs/no-such-run/nodes/inp/input",
            json={"data": "x"},
        )
        assert resp.status_code == 404
