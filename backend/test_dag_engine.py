#!/usr/bin/env python3
# @file test_dag_engine.py
# @brief 简单测试 DAG 工作流引擎
# @create 2026-04-01

import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    print("Testing imports...")

    from app.runtime import (
        ActionNode,
        ActionRegistry,
        DAGScheduler,
        DAGWorkflow,
        DataRouter,
        Edge,
        EndNode,
        InputPort,
        NodeExecutor,
        NodeStatus,
        OutputPort,
        PassNode,
        StartNode,
        WorkflowRunner,
        WorkflowStatus,
        get_action_registry,
        register_builtin_actions,
    )

    print("✓ All imports successful")

    print("\nTesting ActionRegistry...")
    registry = get_action_registry()
    print(f"✓ ActionRegistry created, available actions: {registry.list_actions()}")

    print("\nTesting DAG model creation...")

    start_node = StartNode(
        id="start",
        name="Start",
        outputs=[
            OutputPort(id="input1", name="Input 1", type="string", required=True),
        ],
    )

    action_node = ActionNode(
        id="action1",
        name="Log Action",
        action_type="log",
        inputs=[
            InputPort(id="message", name="Message", type="string", required=True),
        ],
        outputs=[
            OutputPort(id="output", name="Output", type="any", required=True),
        ],
    )

    pass_node = PassNode(
        id="pass1",
        name="Pass Through",
        inputs=[
            InputPort(id="input", name="Input", type="any", required=True),
        ],
        outputs=[
            OutputPort(id="output", name="Output", type="any", required=True),
        ],
    )

    end_node = EndNode(
        id="end",
        name="End",
        inputs=[
            InputPort(id="result", name="Result", type="any", required=True),
        ],
    )

    workflow = DAGWorkflow(
        name="Test Workflow",
        nodes={
            "start": start_node,
            "action1": action_node,
            "pass1": pass_node,
            "end": end_node,
        },
        edges=[
            Edge(id="e1", source="start.input1", target="action1.message"),
            Edge(id="e2", source="action1.output", target="pass1.input"),
            Edge(id="e3", source="pass1.output", target="end.result"),
        ],
    )

    print("✓ DAGWorkflow created successfully")
    print(f"  - Nodes: {list(workflow.nodes.keys())}")
    print(f"  - Edges: {len(workflow.edges)}")

    print("\nTesting WorkflowRunner...")
    runner = WorkflowRunner(workflow)
    print("✓ WorkflowRunner created")

    print("\n✓ All basic tests passed!")

except Exception as e:
    print(f"✗ Test failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
