import pytest

from app.runtime.dag_models import OutputPort
from app.runtime.nodes import SplitNode


def test_split_node_initialization():
    node = SplitNode(id="split1", name="Test Split")
    assert node.id == "split1"
    assert node.name == "Test Split"
    assert node.type == "split"
    assert len(node.inputs) == 1
    assert node.inputs[0].id == "input"
    assert node.config.get("strategy") == "by_index"


def test_split_node_by_index_strategy():
    port1 = OutputPort(id="output1", name="Output 1", type="any", index=0)
    port2 = OutputPort(id="output2", name="Output 2", type="any", index=1)
    node = SplitNode(id="split1", outputs=[port1, port2])

    result = node.execute({"input": ["a", "b", "c"]})
    assert result["output1"] == "a"
    assert result["output2"] == "b"


def test_split_node_by_index_out_of_bounds():
    port1 = OutputPort(id="output1", name="Output 1", type="any", index=10)
    node = SplitNode(id="split1", outputs=[port1])

    result = node.execute({"input": ["a", "b"]})
    assert "output1" not in result


def test_split_node_by_index_non_list_input():
    port1 = OutputPort(id="output1", name="Output 1", type="any", index=0)
    node = SplitNode(id="split1", outputs=[port1])

    result = node.execute({"input": "not a list"})
    assert "output1" not in result


def test_split_node_by_field_strategy():
    port1 = OutputPort(id="output1", name="Output 1", type="any", field="name")
    port2 = OutputPort(id="output2", name="Output 2", type="any", field="age")
    node = SplitNode(
        id="split1",
        config={"strategy": "by_field"},
        outputs=[port1, port2],
    )

    result = node.execute({"input": {"name": "Alice", "age": 25, "city": "Beijing"}})
    assert result["output1"] == "Alice"
    assert result["output2"] == 25


def test_split_node_by_field_missing_field():
    port1 = OutputPort(id="output1", name="Output 1", type="any", field="missing")
    node = SplitNode(
        id="split1",
        config={"strategy": "by_field"},
        outputs=[port1],
    )

    result = node.execute({"input": {"name": "Alice"}})
    assert "output1" not in result


def test_split_node_by_field_non_object_input():
    port1 = OutputPort(id="output1", name="Output 1", type="any", field="name")
    node = SplitNode(
        id="split1",
        config={"strategy": "by_field"},
        outputs=[port1],
    )

    result = node.execute({"input": "not an object"})
    assert "output1" not in result


def test_split_node_custom_strategy():
    port1 = OutputPort(id="output1", name="Output 1", type="any")
    port2 = OutputPort(id="output2", name="Output 2", type="any")
    node = SplitNode(
        id="split1",
        config={
            "strategy": "custom",
            "custom_strategy": "{'output1': input[0], 'output2': input[1]}",
        },
        outputs=[port1, port2],
    )

    result = node.execute({"input": ["x", "y"]})
    assert result["output1"] == "x"
    assert result["output2"] == "y"


def test_split_node_custom_strategy_error():
    node = SplitNode(
        id="split1",
        config={"strategy": "custom", "custom_strategy": "invalid syntax!!!"},
    )

    with pytest.raises(ValueError, match="Custom split strategy failed"):
        node.execute({"input": "test"})
