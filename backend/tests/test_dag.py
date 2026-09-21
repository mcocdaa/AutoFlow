# @file /backend/tests/test_dag.py
# @brief DAG 依赖分析、拓扑分层与并发执行引擎单测
# @create 2026-09-20

from __future__ import annotations

import time
from pathlib import Path

import pytest
from app.core.registry import Registry
from app.runtime.dag import (
    DAGCycleError,
    DAGError,
    DAGValidationError,
    detect_cycles,
    resolve_execution_layers,
    validate_dependencies,
)
from app.runtime.models import (
    ActionSpec,
    FlowSpec,
    HookSpec,
    StepSpec,
)
from app.runtime.runner import Runner
from app.runtime.session import RunSession
from app.runtime.storage.store import RunStore


def _make_registry(actions: dict | None = None) -> Registry:
    registry = Registry()
    for name, handler in (actions or {}).items():
        registry.register_action(name, handler)
    return registry


def _echo_action(ctx, params):
    return {"message": params.get("message", "ok"), "input": ctx.input}


def _sleep_echo_action(ctx, params):
    duration = params.get("sleep_seconds", 0.05)
    time.sleep(duration)
    return {"message": params.get("message", "ok"), "slept": duration}


def _fail_action(ctx, params):
    raise RuntimeError(params.get("error_msg", "step failed intentionally"))


# ============================================================================
# 1. DAG 依赖图分析与拓扑分层函数单测
# ============================================================================


class TestDAGAnalysis:
    """测试 validate_dependencies / detect_cycles / resolve_execution_layers"""

    def test_error_hierarchy(self):
        assert issubclass(DAGCycleError, DAGError)
        assert issubclass(DAGValidationError, DAGError)
        assert issubclass(DAGError, ValueError)

    def test_validate_dependencies_valid(self):
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo")),
            StepSpec(id="b", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="c", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="d", action=ActionSpec(type="echo"), depends_on=["b", "c"]),
        ]
        validate_dependencies(steps)
        assert detect_cycles(steps) is False

    def test_validate_dependencies_self_dependency_raises(self):
        steps = [StepSpec(id="a", action=ActionSpec(type="echo"), depends_on=["a"])]
        with pytest.raises(DAGValidationError) as exc_info:
            validate_dependencies(steps)
        assert "cannot depend on itself" in str(exc_info.value)

    def test_validate_dependencies_non_existent_step_raises(self):
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo"), depends_on=["unknown"])
        ]
        with pytest.raises(DAGValidationError) as exc_info:
            validate_dependencies(steps)
        assert "depends on non-existent step 'unknown'" in str(exc_info.value)

    def test_validate_dependencies_duplicate_step_id_raises(self):
        steps = [
            StepSpec(id="dup", action=ActionSpec(type="echo")),
            StepSpec(id="dup", action=ActionSpec(type="echo")),
        ]
        with pytest.raises(DAGValidationError) as exc_info:
            validate_dependencies(steps)
        assert "Duplicate step id detected" in str(exc_info.value)

    def test_detect_cycles_direct_cycle_raises(self):
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo"), depends_on=["b"]),
            StepSpec(id="b", action=ActionSpec(type="echo"), depends_on=["a"]),
        ]
        with pytest.raises(DAGCycleError) as exc_info:
            detect_cycles(steps)
        assert "Cycle detected in DAG" in str(exc_info.value)

    def test_detect_cycles_indirect_cycle_raises(self):
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo"), depends_on=["c"]),
            StepSpec(id="b", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="c", action=ActionSpec(type="echo"), depends_on=["b"]),
        ]
        with pytest.raises(DAGCycleError) as exc_info:
            detect_cycles(steps)
        assert "Cycle detected in DAG" in str(exc_info.value)

    def test_detect_cycles_self_loop_raises(self):
        steps = [StepSpec(id="a", action=ActionSpec(type="echo"), depends_on=["a"])]
        with pytest.raises((DAGCycleError, DAGValidationError)):
            detect_cycles(steps)

    def test_resolve_execution_layers_linear_implicit(self):
        """若均未指定 depends_on，应按线性隐式依赖分层，每步独立一层"""
        steps = [
            StepSpec(id="s1", action=ActionSpec(type="echo")),
            StepSpec(id="s2", action=ActionSpec(type="echo")),
            StepSpec(id="s3", action=ActionSpec(type="echo")),
        ]
        layers = resolve_execution_layers(steps)
        assert len(layers) == 3
        assert [s.id for s in layers[0]] == ["s1"]
        assert [s.id for s in layers[1]] == ["s2"]
        assert [s.id for s in layers[2]] == ["s3"]

    def test_resolve_execution_layers_fork_join(self):
        """A -> B1, B2 并发 -> C 聚合"""
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo")),
            StepSpec(id="b1", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="b2", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="c", action=ActionSpec(type="echo"), depends_on=["b1", "b2"]),
        ]
        layers = resolve_execution_layers(steps)
        assert len(layers) == 3
        assert [s.id for s in layers[0]] == ["a"]
        assert [s.id for s in layers[1]] == ["b1", "b2"]
        assert [s.id for s in layers[2]] == ["c"]

    def test_resolve_execution_layers_diamond(self):
        """菱形结构 A -> B, C -> D"""
        steps = [
            StepSpec(id="a", action=ActionSpec(type="echo")),
            StepSpec(id="b", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="c", action=ActionSpec(type="echo"), depends_on=["a"]),
            StepSpec(id="d", action=ActionSpec(type="echo"), depends_on=["b", "c"]),
        ]
        layers = resolve_execution_layers(steps)
        assert len(layers) == 3
        assert [s.id for s in layers[0]] == ["a"]
        assert [s.id for s in layers[1]] == ["b", "c"]
        assert [s.id for s in layers[2]] == ["d"]

    def test_resolve_execution_layers_complex_multi_layer(self):
        """复杂多层分支与汇合"""
        steps = [
            StepSpec(id="root1", action=ActionSpec(type="echo")),
            StepSpec(id="root2", action=ActionSpec(type="echo")),
            StepSpec(
                id="mid1",
                action=ActionSpec(type="echo"),
                depends_on=["root1"],
            ),
            StepSpec(
                id="mid2",
                action=ActionSpec(type="echo"),
                depends_on=["root1", "root2"],
            ),
            StepSpec(
                id="sink",
                action=ActionSpec(type="echo"),
                depends_on=["mid1", "mid2"],
            ),
        ]
        layers = resolve_execution_layers(steps)
        assert len(layers) == 3
        assert [s.id for s in layers[0]] == ["root1", "root2"]
        assert [s.id for s in layers[1]] == ["mid1", "mid2"]
        assert [s.id for s in layers[2]] == ["sink"]

    def test_resolve_execution_layers_empty(self):
        assert resolve_execution_layers([]) == []


# ============================================================================
# 2. DAG 与线性模式执行引擎集成测试 (Session / Runner)
# ============================================================================


class TestDAGExecutionEngine:
    """测试 Session / Runner 执行引擎对线性隐式与 DAG 并发拓扑的兼容与执行"""

    def test_linear_implicit_backward_compatibility(self, tmp_path: Path):
        """测试 100% 向后兼容: 未指定 depends_on 时保持既有线性执行"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry({"test.echo": _echo_action})

        flow = FlowSpec(
            version="1.0",
            name="linear-flow",
            steps=[
                StepSpec(
                    id="s1",
                    action=ActionSpec(type="test.echo", params={"message": "step1"}),
                    output_var="out1",
                ),
                StepSpec(
                    id="s2",
                    action=ActionSpec(type="test.echo", params={"message": "step2"}),
                ),
            ],
        )

        runner = Runner(registry, store)
        result = runner.run_flow(flow, input="flow-input")

        assert result.status == "success"
        assert len(result.steps) == 2
        assert result.steps[0].step_id == "s1"
        assert result.steps[0].action_output == {
            "message": "step1",
            "input": "flow-input",
        }
        assert result.steps[1].step_id == "s2"
        # 线性模式下，第二个步骤的 input 自动接收上一步的 action_output
        assert result.steps[1].action_output["input"] == {
            "message": "step1",
            "input": "flow-input",
        }

    def test_fork_join_concurrent_execution(self, tmp_path: Path):
        """测试 Fork-Join 拓扑结构: A -> B1, B2 并发执行 -> C 聚合"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry(
            {
                "test.echo": _echo_action,
                "test.sleep_echo": _sleep_echo_action,
            }
        )

        flow = FlowSpec(
            version="1.0",
            name="fork-join-flow",
            steps=[
                StepSpec(
                    id="step_a",
                    action=ActionSpec(type="test.echo", params={"message": "from_a"}),
                ),
                StepSpec(
                    id="step_b1",
                    action=ActionSpec(
                        type="test.sleep_echo",
                        params={"message": "from_b1", "sleep_seconds": 0.08},
                    ),
                    depends_on=["step_a"],
                ),
                StepSpec(
                    id="step_b2",
                    action=ActionSpec(
                        type="test.sleep_echo",
                        params={"message": "from_b2", "sleep_seconds": 0.08},
                    ),
                    depends_on=["step_a"],
                ),
                StepSpec(
                    id="step_c",
                    action=ActionSpec(
                        type="test.echo",
                        params={
                            "b1_msg": "{{steps.step_b1.output.message}}",
                            "b2_msg": "{{steps.step_b2.output.message}}",
                        },
                    ),
                    depends_on=["step_b1", "step_b2"],
                ),
            ],
        )

        runner = Runner(registry, store, max_workers=4)
        start_t = time.perf_counter()
        result = runner.run_flow(flow)
        elapsed = time.perf_counter() - start_t

        assert result.status == "success"
        assert len(result.steps) == 4
        # 耗时应该接近 0.08s 而不是 0.16s (说明 b1 与 b2 确实并发执行)
        assert elapsed < 0.15

        step_map = {s.step_id: s for s in result.steps}
        assert step_map["step_a"].status == "success"
        assert step_map["step_b1"].status == "success"
        assert step_map["step_b2"].status == "success"
        assert step_map["step_c"].status == "success"

        # 聚合步骤正确拿到 b1 与 b2 的输出
        c_output = step_map["step_c"].action_output
        assert c_output["message"] == "ok"
        # 且 ctx.input 包含了来自 b1 和 b2 的输入字典
        assert "step_b1" in c_output["input"]
        assert "step_b2" in c_output["input"]

    def test_cycle_dependency_raises_on_start(self, tmp_path: Path):
        """测试存在循环依赖的 Flow 在启动时抛出明确异常"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry({"test.echo": _echo_action})

        flow = FlowSpec(
            version="1.0",
            name="cycle-flow",
            steps=[
                StepSpec(
                    id="s1",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["s2"],
                ),
                StepSpec(
                    id="s2",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["s1"],
                ),
            ],
        )

        runner = Runner(registry, store)
        with pytest.raises(DAGCycleError):
            runner.run_flow(flow)

    def test_invalid_dependency_step_id_raises_on_start(self, tmp_path: Path):
        """测试引用不存在的 step_id 在启动时抛出明确异常"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry({"test.echo": _echo_action})

        flow = FlowSpec(
            version="1.0",
            name="invalid-dep-flow",
            steps=[
                StepSpec(
                    id="s1",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["ghost_step"],
                ),
            ],
        )

        runner = Runner(registry, store)
        with pytest.raises(DAGValidationError):
            runner.run_flow(flow)

    def test_dag_failure_stops_downstream_and_triggers_hooks(self, tmp_path: Path):
        """测试并发分支中一步骤失败时，后续步骤停止执行并触发 on_failure hooks"""
        store = RunStore(artifacts_dir=tmp_path)

        def _hook_action(ctx, params):
            return {"hook": "failure_caught"}

        registry = _make_registry(
            {
                "test.echo": _echo_action,
                "test.fail": _fail_action,
                "test.hook": _hook_action,
            }
        )

        flow = FlowSpec(
            version="1.0",
            name="dag-failure-flow",
            steps=[
                StepSpec(
                    id="root",
                    action=ActionSpec(type="test.echo", params={}),
                ),
                StepSpec(
                    id="b1",
                    action=ActionSpec(
                        type="test.fail",
                        params={"error_msg": "branch 1 broke"},
                    ),
                    depends_on=["root"],
                ),
                StepSpec(
                    id="b2",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["root"],
                ),
                StepSpec(
                    id="sink",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["b1", "b2"],
                ),
            ],
            hooks=HookSpec(on_failure=[ActionSpec(type="test.hook", params={})]),
        )

        runner = Runner(registry, store)
        result = runner.run_flow(flow)

        assert result.status == "failed"
        assert result.error is not None and "branch 1 broke" in result.error
        step_ids = [s.step_id for s in result.steps]
        # root, b1, b2 应该执行了，但 sink 不会执行
        assert "root" in step_ids
        assert "b1" in step_ids
        assert "b2" in step_ids
        assert "sink" not in step_ids

        # 触发了 on_failure hook
        assert len(result.hook_results) == 1
        assert result.hook_results[0].status == "success"
        assert result.hook_results[0].hook == "on_failure"

    def test_dag_condition_skipped_step(self, tmp_path: Path):
        """测试 DAG 中某些分支条件不满足被跳过"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry({"test.echo": _echo_action})

        flow = FlowSpec(
            version="1.0",
            name="dag-condition-flow",
            steps=[
                StepSpec(
                    id="root",
                    action=ActionSpec(type="test.echo", params={}),
                ),
                StepSpec(
                    id="b_skip",
                    action=ActionSpec(type="test.echo", params={}),
                    condition="1 == 2",
                    depends_on=["root"],
                ),
                StepSpec(
                    id="b_run",
                    action=ActionSpec(type="test.echo", params={"message": "ran"}),
                    depends_on=["root"],
                ),
                StepSpec(
                    id="sink",
                    action=ActionSpec(type="test.echo", params={}),
                    depends_on=["b_run"],
                ),
            ],
        )

        runner = Runner(registry, store)
        result = runner.run_flow(flow)

        assert result.status == "success"
        step_map = {s.step_id: s for s in result.steps}
        assert step_map["b_skip"].status == "skipped"
        assert step_map["b_run"].status == "success"
        assert step_map["sink"].status == "success"

    def test_dag_state_roundtrip_pause_and_resume(self, tmp_path: Path):
        """测试 DAG 执行会话单层步进、落盘状态序列化、跨实例恢复续跑"""
        store = RunStore(artifacts_dir=tmp_path)
        registry = _make_registry({"test.echo": _echo_action})

        flow = FlowSpec(
            version="1.0",
            name="dag-pause-flow",
            steps=[
                StepSpec(
                    id="a",
                    action=ActionSpec(type="test.echo", params={"message": "A"}),
                ),
                StepSpec(
                    id="b",
                    action=ActionSpec(type="test.echo", params={"message": "B"}),
                    depends_on=["a"],
                ),
                StepSpec(
                    id="c",
                    action=ActionSpec(type="test.echo", params={"message": "C"}),
                    depends_on=["b"],
                ),
            ],
        )

        session = RunSession.start(registry, store, flow)
        assert session.finished is False

        # 执行第一层 (a)
        session.step()
        assert len(session.run.steps) == 1
        assert session.run.steps[0].step_id == "a"

        # 序列化状态
        state = session.to_state()

        # 跨实例从状态恢复
        resumed = RunSession.from_state(registry, store, state)
        assert resumed.finished is False
        assert len(resumed.run.steps) == 1

        # 续跑到结束 (执行 b 和 c)
        resumed.run_to_completion()
        assert resumed.finished is True
        assert resumed.run.status == "success"
        assert [s.step_id for s in resumed.run.steps] == ["a", "b", "c"]

    def test_thread_safety_concurrent_artifact_writes(self, tmp_path: Path):
        """测试高并发下多个步骤同时产生产物与状态更新时的线程安全"""
        store = RunStore(artifacts_dir=tmp_path)

        def _big_output_action(ctx, params):
            # 产生大于 64KB 的字典输出以触发 externalize_if_large 产物写入
            return {"data": "x" * 70000, "idx": params.get("idx")}

        registry = _make_registry({"test.big": _big_output_action})

        # 构造一层包含 10 个完全并发的步骤
        steps = [
            StepSpec(
                id=f"step_{i}",
                action=ActionSpec(type="test.big", params={"idx": i}),
                depends_on=[],
            )
            for i in range(10)
        ]
        flow = FlowSpec(
            version="1.0",
            name="concurrent-artifact-flow",
            steps=steps,
        )

        runner = Runner(registry, store, max_workers=10)
        result = runner.run_flow(flow)

        assert result.status == "success"
        assert len(result.steps) == 10
        for s in result.steps:
            assert s.status == "success"
            # 确认输出被正常外置为产物引用
            assert isinstance(s.action_output, dict)
            assert "__artifact__" in s.action_output
            rel_path = s.action_output["__artifact__"]["path"]
            artifact_file = store.artifacts_dir / result.run_id / rel_path
            assert artifact_file.is_file()

        # 校验持久化的 run.json 读取完整正常
        saved_run = store.get_run(result.run_id)
        assert saved_run is not None
        assert saved_run.status == "success"
        assert len(saved_run.steps) == 10
