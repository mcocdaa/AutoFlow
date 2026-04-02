import pytest

from app.runtime.dag_models import (
    DAGWorkflow,
    Edge,
    InputPort,
    OutputPort,
)
from app.runtime.nodes import (
    EndNode,
    PassNode,
    StartNode,
)
from app.runtime.yaml_exporter import YAMLExporter
from app.runtime.yaml_loader import YAMLLoader, YAMLLoaderError

BASIC_WORKFLOW_YAML = """
version: "2.0"
name: "Test Workflow"
description: "A test workflow"

nodes:
  start:
    type: "start"
    name: "Start"
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  pass1:
    type: "pass"
    name: "Pass 1"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  end:
    type: "end"
    name: "End"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true

edges:
  - source: "start.output"
    target: "pass1.input"
  - source: "pass1.output"
    target: "end.input"
"""


def test_yaml_loader_basic_workflow():
    workflow = YAMLLoader.load(BASIC_WORKFLOW_YAML)
    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow"
    assert "start" in workflow.nodes
    assert "pass1" in workflow.nodes
    assert "end" in workflow.nodes
    assert len(workflow.edges) == 2


def test_yaml_loader_version_validation():
    invalid_yaml = """
version: "1.0"
name: "Test"
nodes: {}
edges: []
"""
    with pytest.raises(YAMLLoaderError, match="Unsupported version"):
        YAMLLoader.load(invalid_yaml)


def test_yaml_loader_missing_required_fields():
    missing_name = """
version: "2.0"
nodes: {}
edges: []
"""
    with pytest.raises(YAMLLoaderError, match="Missing required field: name"):
        YAMLLoader.load(missing_name)


def test_yaml_loader_cycle_detection():
    cyclic_yaml = """
version: "2.0"
name: "Cyclic Workflow"

nodes:
  start:
    type: "start"
    name: "Start"
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  node1:
    type: "pass"
    name: "Node 1"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  node2:
    type: "pass"
    name: "Node 2"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  end:
    type: "end"
    name: "End"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true

edges:
  - source: "start.output"
    target: "node1.input"
  - source: "node1.output"
    target: "node2.input"
  - source: "node2.output"
    target: "node1.input"
  - source: "node2.output"
    target: "end.input"
"""
    with pytest.raises(YAMLLoaderError, match="Workflow contains a cycle"):
        YAMLLoader.load(cyclic_yaml)


def test_yaml_exporter_basic_workflow():
    start = StartNode(
        id="start",
        name="Start",
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    pass1 = PassNode(
        id="pass1",
        name="Pass 1",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    end = EndNode(
        id="end",
        name="End",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
    )

    workflow = DAGWorkflow(
        name="Test Workflow",
        description="A test workflow",
        nodes={"start": start, "pass1": pass1, "end": end},
        edges=[
            Edge(id="e1", source="start.output", target="pass1.input"),
            Edge(id="e2", source="pass1.output", target="end.input"),
        ],
    )

    yaml_str = YAMLExporter.export(workflow)
    assert "version:" in yaml_str
    assert "2.0" in yaml_str
    assert "name: Test Workflow" in yaml_str
    assert "start:" in yaml_str
    assert "pass1:" in yaml_str
    assert "end:" in yaml_str


def test_export_import_consistency():
    start = StartNode(
        id="start",
        name="Start",
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    pass1 = PassNode(
        id="pass1",
        name="Pass 1",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    end = EndNode(
        id="end",
        name="End",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
    )

    original = DAGWorkflow(
        name="Test Workflow",
        description="A test workflow",
        nodes={"start": start, "pass1": pass1, "end": end},
        edges=[
            Edge(id="e1", source="start.output", target="pass1.input"),
            Edge(id="e2", source="pass1.output", target="end.input"),
        ],
    )

    yaml_str = YAMLExporter.export(original)
    reloaded = YAMLLoader.load(yaml_str)

    assert original.name == reloaded.name
    assert original.description == reloaded.description
    assert set(original.nodes.keys()) == set(reloaded.nodes.keys())
    assert len(original.edges) == len(reloaded.edges)


def test_yaml_loader_invalid_port_ref():
    invalid_yaml = """
version: "2.0"
name: "Test"

nodes:
  start:
    type: "start"
    name: "Start"
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
  end:
    type: "end"
    name: "End"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true

edges:
  - source: "start.nonexistent"
    target: "end.input"
"""
    with pytest.raises(YAMLLoaderError, match="Source port not found"):
        YAMLLoader.load(invalid_yaml)


def test_yaml_loader_missing_start_node():
    missing_start = """
version: "2.0"
name: "Test"

nodes:
  end:
    type: "end"
    name: "End"
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true

edges: []
"""
    with pytest.raises(YAMLLoaderError, match="Workflow must have a Start node"):
        YAMLLoader.load(missing_start)
