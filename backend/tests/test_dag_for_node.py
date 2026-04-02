import pytest

from app.runtime.nodes import ForNode


def test_for_node_initialization():
    node = ForNode(id="for1", name="Test For")
    assert node.id == "for1"
    assert node.name == "Test For"
    assert node.type == "for"
    assert len(node.inputs) == 1
    assert node.inputs[0].id == "items"
    assert len(node.outputs) == 1
    assert node.outputs[0].id == "results"


def test_for_node_basic_loop():
    node = ForNode(id="for1")

    result = node.execute({"items": [1, 2, 3]})
    assert result["results"] == [1, 2, 3]


def test_for_node_with_handler():
    def double(x):
        return x * 2

    node = ForNode(id="for1")

    result = node.execute({"items": [1, 2, 3]}, item_handler=double)
    assert result["results"] == [2, 4, 6]


def test_for_node_non_list_input():
    node = ForNode(id="for1")

    with pytest.raises(ValueError, match="Input must be a list"):
        node.execute({"items": "not a list"})


def test_for_node_empty_list():
    node = ForNode(id="for1")

    result = node.execute({"items": []})
    assert result["results"] == []
