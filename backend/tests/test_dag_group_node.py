import pytest

from app.runtime.dag_models import (
    GroupConfig,
    InputMapping,
    InputPort,
    InternalSubgraph,
    OutputMapping,
    OutputPort,
)
from app.runtime.nodes import GroupNode, PassNode


def test_group_node_initialization():
    node = GroupNode(id="group1", name="Test Group")
    assert node.id == "group1"
    assert node.name == "Test Group"
    assert node.type == "group"


def test_group_node_config():
    internal_subgraph = InternalSubgraph()
    group_config = GroupConfig(
        internal_subgraph=internal_subgraph,
        input_mappings=[],
        output_mappings=[],
    )
    node = GroupNode(id="group1", config={"group_config": group_config.model_dump()})
    assert node.group_config.internal_subgraph is not None


def test_group_node_with_internal_nodes():
    pass_node = PassNode(
        id="pass1",
        name="Pass",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    internal_subgraph = InternalSubgraph(nodes={"pass1": pass_node}, edges=[])
    group_config = GroupConfig(
        internal_subgraph=internal_subgraph,
        input_mappings=[
            InputMapping(
                external_port_id="input",
                internal_node_id="pass1",
                internal_port_id="input",
            ),
        ],
        output_mappings=[
            OutputMapping(
                external_port_id="output",
                internal_node_id="pass1",
                internal_port_id="output",
            ),
        ],
    )
    node = GroupNode(
        id="group1",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
        config={"group_config": group_config.model_dump()},
    )

    node._internal_nodes_cache = {"pass1": pass_node}

    result = node.execute({"input": "test"})
    assert "output" in result
    assert result["output"] == "test"


def test_group_node_empty_subgraph():
    node = GroupNode(id="group1")
    result = node.execute({})
    assert result == {}


def test_group_node_multiple_mappings():
    pass_node1 = PassNode(
        id="pass1",
        name="Pass 1",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    pass_node2 = PassNode(
        id="pass2",
        name="Pass 2",
        inputs=[InputPort(id="input", name="Input", type="any", required=True)],
        outputs=[OutputPort(id="output", name="Output", type="any")],
    )
    internal_subgraph = InternalSubgraph(
        nodes={"pass1": pass_node1, "pass2": pass_node2},
        edges=[],
    )
    group_config = GroupConfig(
        internal_subgraph=internal_subgraph,
        input_mappings=[
            InputMapping(
                external_port_id="in1",
                internal_node_id="pass1",
                internal_port_id="input",
            ),
            InputMapping(
                external_port_id="in2",
                internal_node_id="pass2",
                internal_port_id="input",
            ),
        ],
        output_mappings=[
            OutputMapping(
                external_port_id="out1",
                internal_node_id="pass1",
                internal_port_id="output",
            ),
            OutputMapping(
                external_port_id="out2",
                internal_node_id="pass2",
                internal_port_id="output",
            ),
        ],
    )
    node = GroupNode(
        id="group1",
        inputs=[
            InputPort(id="in1", name="In1", type="any", required=True),
            InputPort(id="in2", name="In2", type="any", required=True),
        ],
        outputs=[
            OutputPort(id="out1", name="Out1", type="any"),
            OutputPort(id="out2", name="Out2", type="any"),
        ],
        config={"group_config": group_config.model_dump()},
    )

    node._internal_nodes_cache = {"pass1": pass_node1, "pass2": pass_node2}

    result = node.execute({"in1": "value1", "in2": "value2"})
    assert result["out1"] == "value1"
    assert result["out2"] == "value2"
