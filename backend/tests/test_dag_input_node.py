# @file /backend/tests/test_dag_input_node.py
# @brief TDD tests for InputNode

from __future__ import annotations

import pytest

from app.runtime.nodes.input import InputNode


def test_input_node_created_with_correct_ports():
    node = InputNode(id="input_1", name="My Input")
    assert node.type == "input"
    assert node.inputs == []
    assert len(node.outputs) == 1
    assert node.outputs[0].id == "output"
    assert node.error_port is not None
    assert node.error_port.id == "error"


def test_input_node_execute_returns_ext_data():
    node = InputNode(id="input_1")
    result = node.execute({"__ext__": "hello from outside"})
    assert result == {"output": "hello from outside"}


def test_input_node_execute_with_none_ext():
    node = InputNode(id="input_1")
    result = node.execute({})
    assert result == {"output": None}


def test_input_node_execute_with_dict_data():
    node = InputNode(id="input_1")
    data = {"key": "value", "count": 42}
    result = node.execute({"__ext__": data})
    assert result == {"output": data}
