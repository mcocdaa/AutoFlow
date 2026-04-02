import pytest

from app.runtime.dag_models import OutputPort
from app.runtime.nodes import IfNode


def test_if_node_initialization():
    node = IfNode(id="if1", name="Test If")
    assert node.id == "if1"
    assert node.name == "Test If"
    assert node.type == "if"
    assert len(node.inputs) == 1
    assert node.inputs[0].id == "input"


def test_if_node_condition_matching():
    port1 = OutputPort(id="true", name="True", type="any", condition="input > 5")
    port2 = OutputPort(id="false", name="False", type="any", condition="input <= 5")
    node = IfNode(id="if1", outputs=[port1, port2])

    result = node.execute({"input": 10})
    assert "true" in result
    assert "false" not in result


def test_if_node_default_branch():
    port1 = OutputPort(id="case1", name="Case 1", type="any", condition="input == 'a'")
    port2 = OutputPort(id="default", name="Default", type="any")
    node = IfNode(id="if1", outputs=[port1, port2])

    result = node.execute({"input": "b"})
    assert "case1" not in result
    assert "default" in result


def test_if_node_first_matching_wins():
    port1 = OutputPort(id="port1", name="Port 1", type="any", condition="input > 0")
    port2 = OutputPort(id="port2", name="Port 2", type="any", condition="input > 5")
    node = IfNode(id="if1", outputs=[port1, port2])

    result = node.execute({"input": 10})
    assert "port1" in result
    assert "port2" not in result


def test_if_node_invalid_condition():
    port1 = OutputPort(
        id="port1", name="Port 1", type="any", condition="invalid syntax!!!"
    )
    node = IfNode(id="if1", outputs=[port1])

    with pytest.raises(ValueError, match="Condition evaluation failed"):
        node.execute({"input": 5})
