import pytest

from app.runtime.dag_models import OutputPort
from app.runtime.nodes import SwitchNode


def test_switch_node_initialization():
    node = SwitchNode(id="switch1", name="Test Switch")
    assert node.id == "switch1"
    assert node.name == "Test Switch"
    assert node.type == "switch"
    assert len(node.inputs) == 1
    assert node.inputs[0].id == "input"


def test_switch_node_case_matching():
    port1 = OutputPort(id="case_a", name="Case A", type="any", case="a")
    port2 = OutputPort(id="case_b", name="Case B", type="any", case="b")
    node = SwitchNode(id="switch1", outputs=[port1, port2])

    result = node.execute({"input": "a"})
    assert "case_a" in result
    assert "case_b" not in result


def test_switch_node_default_branch():
    port1 = OutputPort(id="case_a", name="Case A", type="any", case="a")
    port2 = OutputPort(id="default", name="Default", type="any")
    node = SwitchNode(id="switch1", outputs=[port1, port2])

    result = node.execute({"input": "c"})
    assert "case_a" not in result
    assert "default" in result


def test_switch_node_numeric_case():
    port1 = OutputPort(id="case_1", name="Case 1", type="any", case=1)
    port2 = OutputPort(id="case_2", name="Case 2", type="any", case=2)
    node = SwitchNode(id="switch1", outputs=[port1, port2])

    result = node.execute({"input": 2})
    assert "case_1" not in result
    assert "case_2" in result


def test_switch_node_no_match_no_default():
    port1 = OutputPort(id="case_a", name="Case A", type="any", case="a")
    port2 = OutputPort(id="case_b", name="Case B", type="any", case="b")
    node = SwitchNode(id="switch1", outputs=[port1, port2])

    result = node.execute({"input": "c"})
    assert len(result) == 0
