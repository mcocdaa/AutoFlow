# @file /backend/app/runtime/__init__.py
# @brief 运行时核心模块 - Registry/Runner/Store 单例初始化（基于 Hook 模式）
# @create 2026-03-15
# @update 2026-03-27 重构为基于 Hook 的插件系统
# @update 2026-03-30 简化目录结构
# @update 2026-04-01 添加 DAG 工作流引擎核心模块

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.registry import registry
from app.runtime.actions import (
    ActionRegistry,
    get_action_registry,
    register_builtin_actions,
)
from app.runtime.builtins import register_builtins
from app.runtime.dag_models import (
    BaseNode,
    DAGWorkflow,
    Edge,
    InputPort,
    Message,
    MessageMetadata,
    OutputPort,
    PortDataType,
    RetrySpec,
)
from app.runtime.data_router import ConditionEvaluator, DataRouter
from app.runtime.execution_state import (
    ExecutionHistory,
    ExecutionState,
    NodeExecutionRecord,
    NodeStatus,
    VariableScope,
    WorkflowStatus,
)
from app.runtime.executor import NodeExecutor
from app.runtime.nodes import (
    ActionNode,
    EndNode,
    ForNode,
    GroupNode,
    IfNode,
    MergeNode,
    PassNode,
    RetryNode,
    SplitNode,
    StartNode,
    SubflowNode,
    SwitchNode,
    WhileNode,
)
from app.runtime.scheduler import DAGScheduler
from app.runtime.store import RunStore, WorkflowStore
from app.runtime.websocket_manager import WebSocketManager, get_websocket_manager
from app.runtime.workflow_runner import WorkflowRunner


@lru_cache(maxsize=1)
def get_registry():
    """获取全局 registry（已通过 hook 注册了所有插件）"""
    register_builtins(registry)
    return registry


@lru_cache(maxsize=1)
def get_run_store() -> RunStore:
    """获取全局 RunStore 单例（v2 API 使用）"""
    return RunStore()


@lru_cache(maxsize=1)
def get_workflow_store() -> WorkflowStore:
    """获取全局 WorkflowStore 单例"""
    return WorkflowStore()


@lru_cache(maxsize=1)
def get_store() -> RunStore:
    """获取全局 RunStore 单例（向后兼容）"""
    return get_run_store()


__all__ = [
    "get_registry",
    "get_store",
    "get_run_store",
    "get_workflow_store",
    "ActionRegistry",
    "get_action_registry",
    "register_builtin_actions",
    "BaseNode",
    "DAGWorkflow",
    "Edge",
    "InputPort",
    "Message",
    "MessageMetadata",
    "OutputPort",
    "PortDataType",
    "RetrySpec",
    "ConditionEvaluator",
    "DataRouter",
    "ExecutionHistory",
    "ExecutionState",
    "NodeExecutionRecord",
    "NodeStatus",
    "VariableScope",
    "WorkflowStatus",
    "NodeExecutor",
    "StartNode",
    "EndNode",
    "ActionNode",
    "PassNode",
    "MergeNode",
    "SplitNode",
    "IfNode",
    "SwitchNode",
    "ForNode",
    "WhileNode",
    "RetryNode",
    "GroupNode",
    "SubflowNode",
    "DAGScheduler",
    "WorkflowRunner",
    "WebSocketManager",
    "get_websocket_manager",
]
