# @file /backend/app/mcp/tools.py
# @brief MCP 工具实现:能力发现、Flow 执行(同步/异步)、查询、回放、产物读取
# @create 2026-09-18

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.registry import Registry
from app.mcp.flows import resolve_flow, scan_flows
from app.runtime.loaders import load_flow_spec_from_yaml_text
from app.runtime.models import RunResult
from app.runtime.runner import Runner
from app.runtime.session import RunSession
from app.runtime.storage.store import RunStore

DEFAULT_ARTIFACT_MAX_BYTES = 262144


@dataclass(frozen=True)
class McpDeps:
    """工具依赖(显式注入,便于单测)"""

    registry: Registry
    store: RunStore
    runner: Runner
    flows_dir: Path


def _run_json(run: RunResult) -> dict[str, Any]:
    return run.model_dump(mode="json")


def _resolve_flow_yaml(
    deps: McpDeps,
    flow_name: str | None,
    flow_yaml: str | None,
) -> str:
    """解析执行来源:flow_name 与 flow_yaml 必须且只能提供一个"""
    if (flow_name is None) == (flow_yaml is None):
        raise ValueError("必须且只能提供 flow_name 或 flow_yaml 之一")
    if flow_yaml is not None:
        load_flow_spec_from_yaml_text(flow_yaml)
        return flow_yaml
    _, text = resolve_flow(deps.flows_dir, str(flow_name))
    return text


def _load_request(deps: McpDeps, run_id: str) -> dict[str, Any]:
    try:
        return deps.store.get_request(run_id)
    except KeyError as e:
        raise ValueError(f"run has no stored request: {run_id}") from e


def _start_background(session: RunSession) -> None:
    thread = threading.Thread(
        target=session.run_to_completion,
        name=f"mcp-run-{session.run.run_id[:8]}",
        daemon=True,
    )
    thread.start()


def list_capabilities(deps: McpDeps) -> dict[str, Any]:
    """插件/动作/校验发现"""
    return {
        "plugins": [
            {"name": p.name, "version": p.version} for p in deps.registry.list_plugins()
        ],
        "actions": deps.registry.list_actions(),
        "checks": deps.registry.list_checks(),
        "errors": [asdict(e) for e in deps.registry.list_plugin_errors()],
    }


def list_flows(deps: McpDeps) -> dict[str, Any]:
    """列出 flows/ 目录内可用 Flow 与坏文件"""
    entries = scan_flows(deps.flows_dir)
    return {
        "flows_dir": str(deps.flows_dir),
        "flows": [e for e in entries if "error" not in e],
        "errors": [e for e in entries if "error" in e],
    }


def run_flow_sync(
    deps: McpDeps,
    *,
    flow_name: str | None = None,
    flow_yaml: str | None = None,
    input: Any = None,
    vars: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """同步执行到结束并返回 RunResult"""
    text = _resolve_flow_yaml(deps, flow_name, flow_yaml)
    flow = load_flow_spec_from_yaml_text(text)
    request = {"flow_yaml": text, "input": input, "vars": vars or {}}
    result = deps.runner.run_flow(flow, input=input, vars=vars, request=request)
    return _run_json(result)


def start_run_async(
    deps: McpDeps,
    *,
    flow_name: str | None = None,
    flow_yaml: str | None = None,
    input: Any = None,
    vars: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """后台线程执行,立即返回 run_id;进度用 get_run 轮询"""
    text = _resolve_flow_yaml(deps, flow_name, flow_yaml)
    flow = load_flow_spec_from_yaml_text(text)
    request = {"flow_yaml": text, "input": input, "vars": vars or {}}
    session = RunSession.start(
        deps.registry,
        deps.store,
        flow,
        input=input,
        vars=vars,
        request=request,
    )
    _start_background(session)
    return {
        "run_id": session.run.run_id,
        "flow_name": flow.name,
        "status": "running",
    }


def get_run(deps: McpDeps, run_id: str) -> dict[str, Any]:
    """查询单个运行(运行中可见已完成步骤)"""
    try:
        run = deps.store.get_run(run_id)
    except KeyError as e:
        raise ValueError(f"run not found: {run_id}") from e
    return _run_json(run)


def list_runs(deps: McpDeps, limit: int = 20) -> list[dict[str, Any]]:
    """按开始时间倒序返回最近运行"""
    if limit < 1:
        raise ValueError("limit 必须 >= 1")
    return [_run_json(run) for run in deps.store.list_runs()[:limit]]


def replay_run_sync(deps: McpDeps, run_id: str) -> dict[str, Any]:
    """重放已保存请求,同步执行到底"""
    payload = _load_request(deps, run_id)
    text = payload.get("flow_yaml")
    if not isinstance(text, str):
        raise ValueError(f"stored request is invalid: {run_id}")
    flow = load_flow_spec_from_yaml_text(text)
    result = deps.runner.run_flow(
        flow,
        input=payload.get("input"),
        vars=payload.get("vars") or {},
        request=payload,
    )
    return _run_json(result)


def start_replay_async(deps: McpDeps, run_id: str) -> dict[str, Any]:
    """重放已保存请求,后台执行"""
    payload = _load_request(deps, run_id)
    text = payload.get("flow_yaml")
    if not isinstance(text, str):
        raise ValueError(f"stored request is invalid: {run_id}")
    flow = load_flow_spec_from_yaml_text(text)
    session = RunSession.start(
        deps.registry,
        deps.store,
        flow,
        input=payload.get("input"),
        vars=payload.get("vars") or {},
        request=payload,
    )
    _start_background(session)
    return {
        "run_id": session.run.run_id,
        "flow_name": flow.name,
        "status": "running",
    }


def get_artifact(
    deps: McpDeps,
    run_id: str,
    path: str,
    max_bytes: int = DEFAULT_ARTIFACT_MAX_BYTES,
) -> dict[str, Any]:
    """读取运行产物(文本,超限截断;拒绝路径穿越)"""
    if max_bytes < 1:
        raise ValueError("max_bytes 必须 >= 1")
    run_dir = (deps.store.artifacts_dir / run_id).resolve()
    target = (run_dir / path).resolve()
    if not target.is_relative_to(run_dir):
        raise ValueError(f"illegal artifact path: {path}")
    if not target.is_file():
        raise ValueError(f"artifact not found: {path}")
    size = target.stat().st_size
    data = target.read_bytes()[:max_bytes]
    return {
        "run_id": run_id,
        "path": path,
        "size": size,
        "truncated": size > max_bytes,
        "text": data.decode("utf-8", errors="replace"),
    }


def get_flow(deps: McpDeps, flow_name: str) -> dict[str, Any]:
    """获取指定 Flow 的 YAML 源码、步骤结构及说明"""
    path, text = resolve_flow(deps.flows_dir, flow_name)
    flow = load_flow_spec_from_yaml_text(text)
    return {
        "flow_name": flow.name,
        "path": str(path),
        "description": flow.description,
        "steps_count": len(flow.steps),
        "steps": [s.model_dump(mode="json") for s in flow.steps],
        "cron": getattr(flow, "cron", None),
        "raw_yaml": text,
    }


def validate_flow(deps: McpDeps, flow_yaml: str) -> dict[str, Any]:
    """校验 Flow YAML 是否合法"""
    try:
        flow = load_flow_spec_from_yaml_text(flow_yaml)
        return {
            "valid": True,
            "flow_name": flow.name,
            "steps_count": len(flow.steps),
            "error": None,
        }
    except Exception as e:
        return {
            "valid": False,
            "flow_name": None,
            "steps_count": 0,
            "error": str(e),
        }


def time_travel_run(
    deps: McpDeps,
    run_id: str,
    step_index: int,
    run_to_completion: bool = True,
) -> dict[str, Any]:
    """时间旅行回放：从历史 run 的指定步骤分叉并继续执行"""
    source = deps.store.get_run(run_id)
    payload = _load_request(deps, run_id)
    flow_yaml = payload.get("flow_yaml")
    if not isinstance(flow_yaml, str):
        raise ValueError(f"stored request is invalid: {run_id}")
    flow = load_flow_spec_from_yaml_text(flow_yaml)

    session = RunSession.fork_from_run(
        deps.registry,
        deps.store,
        flow,
        source_run=source,
        request=payload,
        next_step_index=step_index,
    )
    if run_to_completion:
        result = session.run_to_completion()
        return _run_json(result)
    else:
        session.step()
        deps.store.save_run(session.run)
        return {
            "session_id": session.run.run_id,
            "run": _run_json(session.run),
            "current_index": session.index,
            "status": session.run.status,
        }


def get_run_diff(deps: McpDeps, run_id_a: str, run_id_b: str) -> dict[str, Any]:
    """步骤级对比两次运行的输出差异、检查结果与错误"""
    run_a = deps.store.get_run(run_id_a)
    run_b = deps.store.get_run(run_id_b)
    from app.runtime.utils.diff import align_steps, step_diff

    steps = [
        step_diff(base_index, base_step, target_index, target_step)
        for base_index, base_step, target_index, target_step in align_steps(
            run_a.steps, run_b.steps
        )
    ]
    return {
        "base_run_id": run_id_a,
        "target_run_id": run_id_b,
        "base_status": run_a.status,
        "target_status": run_b.status,
        "steps": steps,
    }


def search_flow_hub(
    category: str | None = None, query: str | None = None
) -> list[dict[str, Any]]:
    """搜索 Flow Hub 流程市场上的模板"""
    from app.api.v1.hub import CURATED_HUB_FLOWS

    flows = CURATED_HUB_FLOWS
    if category:
        flows = [f for f in flows if f["category"] == category]
    if query:
        q = query.lower()
        flows = [
            f
            for f in flows
            if q in f["name"].lower()
            or q in f["title"].lower()
            or q in f["description"].lower()
        ]
    return flows
