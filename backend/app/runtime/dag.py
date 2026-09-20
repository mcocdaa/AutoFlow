# @file /backend/app/runtime/dag.py
# @brief DAG 依赖分析、循环依赖检测与拓扑分层执行调度
# @create 2026-09-20

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.models import StepSpec

logger = logging.getLogger(__name__)


class DAGError(ValueError):
    """DAG 分析与执行错误基类"""


class DAGValidationError(DAGError):
    """DAG 依赖配置非法(如 step_id 不存在或依赖自身)"""


class DAGCycleError(DAGError):
    """DAG 存在循环依赖"""


def validate_dependencies(steps: list[StepSpec]) -> None:
    """确保 depends_on 引用的 step_id 真实存在且非自身。

    Raises:
        DAGValidationError: 当引用的 step_id 不存在、引用自身或存在重复 step_id 时抛出。
    """
    step_ids: set[str] = set()
    for step in steps:
        if step.id in step_ids:
            raise DAGValidationError(f"Duplicate step id detected: '{step.id}'")
        step_ids.add(step.id)

    for step in steps:
        if not step.depends_on:
            continue
        for dep in step.depends_on:
            if dep == step.id:
                raise DAGValidationError(f"Step '{step.id}' cannot depend on itself.")
            if dep not in step_ids:
                raise DAGValidationError(
                    f"Step '{step.id}' depends on non-existent step '{dep}'."
                )


def detect_cycles(steps: list[StepSpec]) -> bool:
    """循环依赖检测，若发现环抛出明确异常。无环时返回 False。

    Raises:
        DAGCycleError: 当检测到依赖环(包括直接/传递循环依赖)时抛出。
        DAGValidationError: 当依赖配置非法时抛出。
    """
    validate_dependencies(steps)

    # 均未指定 depends_on 时为线性隐式依赖，无环
    if all(s.depends_on is None for s in steps):
        return False

    # 建立邻接表: 依赖关系 step -> dep (即 step 依赖 dep)
    adj: dict[str, list[str]] = {s.id: [] for s in steps}
    for s in steps:
        if s.depends_on:
            for dep in s.depends_on:
                if dep == s.id:
                    raise DAGCycleError(
                        f"Cycle detected in DAG: Step '{s.id}' depends on itself."
                    )
                adj[s.id].append(dep)

    # DFS 检测环: 0=未访问, 1=正在访问(当前递归路径中), 2=已完成
    visited: dict[str, int] = {s.id: 0 for s in steps}
    path: list[str] = []

    def dfs(node: str) -> None:
        visited[node] = 1
        path.append(node)
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                idx = path.index(neighbor)
                cycle_nodes = path[idx:] + [neighbor]
                cycle_str = " -> ".join(cycle_nodes)
                raise DAGCycleError(f"Cycle detected in DAG: {cycle_str}")
            if visited.get(neighbor) == 0:
                dfs(neighbor)
        path.pop()
        visited[node] = 2

    for s in steps:
        if visited[s.id] == 0:
            dfs(s.id)

    return False


def resolve_execution_layers(steps: list[StepSpec]) -> list[list[StepSpec]]:
    """按拓扑层级将 steps 分为多层，同层步骤无相互依赖，可完全并发执行。

    - 若步骤均未指定 depends_on: 采用线性隐式依赖模式，每个步骤单独为一层。
    - 若步骤指定了 depends_on: 基于 Kahn 算法计算入度并分层，
      每层内部保持 steps 原有相对顺序。

    Raises:
        DAGValidationError: 依赖配置非法。
        DAGCycleError: 存在循环依赖。
    """
    if not steps:
        return []

    validate_dependencies(steps)
    detect_cycles(steps)

    # 1. 均未指定 depends_on: 线性隐式依赖
    if all(s.depends_on is None for s in steps):
        return [[step] for step in steps]

    step_map = {s.id: s for s in steps}

    # 2. 存在 depends_on: Kahn 算法拓扑分层
    # 入度: 前置依赖数
    in_degree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {s.id: [] for s in steps}

    for s in steps:
        deps = set(s.depends_on or [])
        in_degree[s.id] = len(deps)
        for dep in deps:
            dependents[dep].append(s.id)

    # 初始可并发层: 入度为 0 的节点(保持原始 steps 顺序)
    current_layer_ids = [s.id for s in steps if in_degree[s.id] == 0]
    if not current_layer_ids and steps:
        raise DAGCycleError("Cycle detected in DAG: no entry step with in-degree 0.")

    layers: list[list[StepSpec]] = []
    processed_count = 0

    while current_layer_ids:
        layers.append([step_map[sid] for sid in current_layer_ids])
        processed_count += len(current_layer_ids)

        next_candidates: list[str] = []
        for sid in current_layer_ids:
            for dep_id in dependents[sid]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    next_candidates.append(dep_id)

        # 保持在原始 steps 中的相对声明顺序
        next_set = set(next_candidates)
        current_layer_ids = [s.id for s in steps if s.id in next_set]

    if processed_count < len(steps):
        raise DAGCycleError("Cycle detected in DAG.")

    return layers
