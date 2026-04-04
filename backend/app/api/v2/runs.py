# @file /backend/app/api/v2/runs.py
# @brief V2 版本执行管理 API

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.runtime import get_store, get_workflow_store
from app.runtime.models import (
    NodeState,
    RunStatus,
    V2InputSubmitRequest,
    V2RunListItem,
    V2RunListResponse,
    V2RunResponse,
    V2RunTriggerRequest,
    V2SuccessResponse,
)
from app.runtime.workflow_runner import WorkflowRunner
from app.runtime.yaml_loader import YAMLLoader

router = APIRouter()


def _build_run_response(run) -> V2RunResponse:
    """将 RunSpec 转换为 V2RunResponse"""
    exec_state = run.execution_state or {}
    return V2RunResponse(
        run_id=run.id,
        workflow_id=run.workflow_id,
        status=RunStatus(run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        node_states={k: NodeState(**v) for k, v in run.node_states.items()},
        error=run.error,
        waiting_node_id=exec_state.get("waiting_node_id"),
    )


@router.post("/workflows/{workflow_id}/runs", response_model=V2RunResponse)
def trigger_run(workflow_id: str, req: V2RunTriggerRequest) -> V2RunResponse:
    """触发工作流执行（V2 版本）"""
    workflow_store = get_workflow_store()
    workflow = workflow_store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")

    run_store = get_store()
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    dag = YAMLLoader.load(workflow.yaml)
    runner = WorkflowRunner(dag, run_id=run_id)
    result = runner.run(inputs=req.inputs)

    waiting_node_id = (
        result.get("waiting_node_id") if result.get("status") == "waiting" else None
    )
    is_waiting = result.get("status") == "waiting"

    if is_waiting:
        run_status = RunStatus.PAUSED.value
    elif runner.state.workflow_status.value == "failed":
        run_status = RunStatus.FAILED.value
    else:
        run_status = RunStatus.COMPLETED.value

    serialized_state: dict | None = None
    if is_waiting:
        serialized_state = runner.serialize_state()
        if waiting_node_id:
            serialized_state["waiting_node_id"] = waiting_node_id

    run = run_store.save_run(
        run_id=run_id,
        workflow_id=workflow_id,
        inputs=req.inputs,
        node_states={},
        status=run_status,
        started_at=started_at,
    )

    if serialized_state is not None:
        run_store.save_execution_state(run_id, serialized_state)

    run = run_store.get_run(run_id)
    return _build_run_response(run)


@router.post("/runs/{run_id}/nodes/{node_id}/input", response_model=V2RunResponse)
def submit_input(run_id: str, node_id: str, req: V2InputSubmitRequest) -> V2RunResponse:
    """向等待输入的节点提交数据，恢复工作流执行"""
    run_store = get_store()
    run = run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status != RunStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="run is not waiting for input")

    state_data = run_store.get_execution_state(run_id)
    if not state_data:
        raise HTTPException(status_code=500, detail="execution state not found")

    workflow_store = get_workflow_store()
    workflow = workflow_store.get_workflow(run.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")

    dag = YAMLLoader.load(workflow.yaml)
    runner = WorkflowRunner(dag, run_id=run_id)
    runner.restore_state(state_data)
    runner.state.available_inputs[f"{node_id}.__ext__"] = req.data

    result = runner.resume()

    waiting_node_id = (
        result.get("waiting_node_id") if result.get("status") == "waiting" else None
    )
    is_waiting = result.get("status") == "waiting"

    if is_waiting:
        new_status = RunStatus.PAUSED.value
        new_state = runner.serialize_state()
        if waiting_node_id:
            new_state["waiting_node_id"] = waiting_node_id
        run_store.save_execution_state(run_id, new_state)
    else:
        if runner.state.workflow_status.value == "failed":
            new_status = RunStatus.FAILED.value
        else:
            new_status = RunStatus.COMPLETED.value
        run_store.save_execution_state(run_id, None)

    run_store.save_run(
        run_id=run_id,
        workflow_id=run.workflow_id,
        inputs=run.inputs,
        node_states={},
        status=new_status,
        started_at=run.started_at,
    )

    run = run_store.get_run(run_id)
    return _build_run_response(run)


@router.post("/runs/{run_id}/cancel", response_model=V2SuccessResponse)
def cancel_run(run_id: str) -> V2SuccessResponse:
    """取消执行（V2 版本）"""
    run_store = get_store()
    run = run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return V2SuccessResponse(success=True)


@router.post("/runs/{run_id}/pause", response_model=V2SuccessResponse)
def pause_run(run_id: str) -> V2SuccessResponse:
    """暂停执行（V2 版本）"""
    run_store = get_store()
    run = run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return V2SuccessResponse(success=True)


@router.post("/runs/{run_id}/resume", response_model=V2SuccessResponse)
def resume_run(run_id: str) -> V2SuccessResponse:
    """继续执行（V2 版本）"""
    run_store = get_store()
    run = run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return V2SuccessResponse(success=True)


@router.get("/runs/{run_id}", response_model=V2RunResponse)
def get_run(run_id: str) -> V2RunResponse:
    """获取执行状态（V2 版本）"""
    run_store = get_store()
    run = run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return _build_run_response(run)


@router.get("/workflows/{workflow_id}/runs", response_model=V2RunListResponse)
def list_runs(
    workflow_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> V2RunListResponse:
    """获取执行历史（V2 版本，支持分页和过滤）"""
    workflow_store = get_workflow_store()
    workflow = workflow_store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")

    run_store = get_store()
    runs = run_store.list_runs(
        page=page,
        page_size=page_size,
        workflow_id=workflow_id,
        status=status,
    )
    total = run_store.count_runs(workflow_id=workflow_id, status=status)

    return V2RunListResponse(
        runs=[
            V2RunListItem(
                run_id=r.id,
                workflow_id=r.workflow_id,
                status=RunStatus(r.status),
                started_at=r.started_at,
                finished_at=r.finished_at,
                duration_ms=r.duration_ms,
            )
            for r in runs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
