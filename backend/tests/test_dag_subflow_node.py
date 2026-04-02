import pytest

from app.runtime.dag_models import (
    DAGWorkflow,
    InputMapping,
    InputPort,
    OutputMapping,
    OutputPort,
    SubflowConfig,
)
from app.runtime.nodes import EndNode, PassNode, StartNode, SubflowNode


def test_subflow_node_initialization():
    node = SubflowNode(id="subflow1", name="Test Subflow")
    assert node.id == "subflow1"
    assert node.name == "Test Subflow"
    assert node.type == "subflow"


def test_subflow_node_config():
    subflow_config = SubflowConfig(
        subflow_id="workflow1",
        subflow_version="v1",
        input_mappings=[],
        output_mappings=[],
    )
    node = SubflowNode(
        id="subflow1", config={"subflow_config": subflow_config.model_dump()}
    )
    assert node.subflow_config.subflow_id == "workflow1"
    assert node.subflow_config.subflow_version == "v1"


def test_subflow_node_circular_reference_detection():
    subflow_config = SubflowConfig(
        subflow_id="workflow1",
        input_mappings=[],
        output_mappings=[],
    )
    node = SubflowNode(
        id="subflow1", config={"subflow_config": subflow_config.model_dump()}
    )
    with pytest.raises(ValueError, match="Circular reference detected"):
        node.execute({}, recursion_stack=["workflow1"])


def test_subflow_node_max_recursion_depth():
    subflow_config = SubflowConfig(
        subflow_id="workflow10",
        input_mappings=[],
        output_mappings=[],
    )
    node = SubflowNode(
        id="subflow1", config={"subflow_config": subflow_config.model_dump()}
    )
    recursion_stack = [f"workflow{i}" for i in range(10)]
    with pytest.raises(ValueError, match="Max recursion depth"):
        node.execute({}, recursion_stack=recursion_stack)


def test_subflow_node_with_loader():
    def mock_loader(subflow_id: str, version: str | None):
        start = StartNode(
            id="start", outputs=[OutputPort(id="output", name="Output", type="any")]
        )
        end = EndNode(
            id="end",
            inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        )
        return DAGWorkflow(
            name="Test Workflow",
            nodes={"start": start, "end": end},
            edges=[],
        )

    subflow_config = SubflowConfig(
        subflow_id="workflow1",
        input_mappings=[
            InputMapping(
                external_port_id="input",
                internal_node_id="start",
                internal_port_id="output",
            ),
        ],
        output_mappings=[
            OutputMapping(
                external_port_id="output",
                internal_node_id="end",
                internal_port_id="input",
            ),
        ],
    )
    node = SubflowNode(
        id="subflow1",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
        config={"subflow_config": subflow_config.model_dump()},
    )

    def mock_executor(subflow, inputs, **kwargs):
        return {"end.input": inputs.get("start.output")}

    result = node.execute(
        {"input": "test"},
        subflow_loader=mock_loader,
        subflow_executor=mock_executor,
    )
    assert "output" in result
    assert result["output"] == "test"


def test_subflow_node_missing_subflow():
    subflow_config = SubflowConfig(
        subflow_id="non_existent",
        input_mappings=[],
        output_mappings=[],
    )
    node = SubflowNode(
        id="subflow1", config={"subflow_config": subflow_config.model_dump()}
    )
    with pytest.raises(ValueError, match="Subflow .* not found"):
        node.execute({})
