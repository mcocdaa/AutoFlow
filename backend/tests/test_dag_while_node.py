import pytest

from app.runtime.nodes import WhileNode


def test_while_node_initialization():
    node = WhileNode(id="while1", name="Test While")
    assert node.id == "while1"
    assert node.name == "Test While"
    assert node.type == "while"
    assert len(node.inputs) == 2
    assert node.inputs[0].id == "initial"
    assert node.inputs[1].id == "condition"
    assert len(node.outputs) == 1
    assert node.outputs[0].id == "result"


def test_while_node_immediate_exit():
    node = WhileNode(id="while1")

    result = node.execute({"initial": 10, "condition": "False"})
    assert result["result"] == 10


def test_while_node_with_handler():
    def increment(x):
        return x + 1

    node = WhileNode(id="while1")

    result = node.execute(
        {"initial": 0, "condition": "current < 3"},
        loop_handler=increment,
        max_iterations=10,
    )
    assert result["result"] == 3


def test_while_node_max_iterations():
    def increment(x):
        return x + 1

    node = WhileNode(id="while1")

    result = node.execute(
        {"initial": 0, "condition": "True"}, loop_handler=increment, max_iterations=5
    )
    assert result["result"] == 5


def test_while_node_invalid_condition():
    node = WhileNode(id="while1")

    with pytest.raises(ValueError, match="Condition evaluation failed"):
        node.execute({"initial": 0, "condition": "invalid syntax!!!"})
