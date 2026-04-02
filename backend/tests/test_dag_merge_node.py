import pytest

from app.runtime.dag_models import InputPort
from app.runtime.nodes import MergeNode


def test_merge_node_initialization():
    node = MergeNode(id="merge1", name="Test Merge")
    assert node.id == "merge1"
    assert node.name == "Test Merge"
    assert node.type == "merge"
    assert len(node.outputs) == 1
    assert node.outputs[0].id == "output"
    assert node.config.get("strategy") == "list_concat"


def test_merge_node_list_concat_strategy():
    node = MergeNode(
        id="merge1",
        inputs=[
            InputPort(id="input1", name="Input 1", type="any"),
            InputPort(id="input2", name="Input 2", type="any"),
        ],
    )

    result = node.execute({"input1": [1, 2], "input2": [3, 4]})
    assert result["output"] == [1, 2, 3, 4]


def test_merge_node_list_concat_non_list_inputs():
    node = MergeNode(
        id="merge1",
        inputs=[
            InputPort(id="input1", name="Input 1", type="any"),
            InputPort(id="input2", name="Input 2", type="any"),
        ],
    )

    result = node.execute({"input1": 1, "input2": [3, 4]})
    assert result["output"] == [1, 3, 4]


def test_merge_node_object_merge_strategy():
    node = MergeNode(
        id="merge1",
        config={"strategy": "object_merge"},
        inputs=[
            InputPort(id="input1", name="Input 1", type="any"),
            InputPort(id="input2", name="Input 2", type="any"),
        ],
    )

    result = node.execute({"input1": {"a": 1, "b": 2}, "input2": {"b": 3, "c": 4}})
    assert result["output"] == {"a": 1, "b": 3, "c": 4}


def test_merge_node_custom_strategy():
    node = MergeNode(
        id="merge1",
        config={
            "strategy": "custom",
            "custom_strategy": "{k: v for k, v in inputs.items()}",
        },
        inputs=[
            InputPort(id="input1", name="Input 1", type="any"),
            InputPort(id="input2", name="Input 2", type="any"),
        ],
    )

    result = node.execute({"input1": "hello", "input2": "world"})
    assert result["output"] == {"input1": "hello", "input2": "world"}


def test_merge_node_custom_strategy_error():
    node = MergeNode(
        id="merge1",
        config={"strategy": "custom", "custom_strategy": "invalid syntax!!!"},
        inputs=[
            InputPort(id="input1", name="Input 1", type="any"),
        ],
    )

    with pytest.raises(ValueError, match="Custom merge strategy failed"):
        node.execute({"input1": "test"})
