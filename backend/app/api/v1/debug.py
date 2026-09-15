# @file /backend/app/api/v1/debug.py
# @brief 调试会话 API:创建/查询/单步/执行到底/删除
# @create 2026-09-15

from __future__ import annotations

from typing import Any, Literal

from app.runtime import get_registry, get_store
from app.runtime.loaders import FlowLoadError, load_flow_spec_from_yaml_text
from app.runtime.models import HookResult, StepResult
from app.runtime.session import RunSession
from app.runtime.storage.session_store import SessionStore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class CreateSessionRequest(BaseModel):
    flow_yaml: str
    input: Any | None = None
    vars: dict[str, Any] = Field(default_factory=dict)


class DebugStepInfo(BaseModel):
    id: str
    name: str | None = None
    for_each: str | None = None
    has_condition: bool = False
    retry_attempts: int = 0
    output_var: str | None = None


class DebugSessionSnapshot(BaseModel):
    session_id: str
    flow_name: str
    status: Literal["paused", "success", "failed"]
    index: int
    total_steps: int
    run_id: str
    steps: list[DebugStepInfo]
    results: list[StepResult]
    hook_results: list[HookResult]
    error: str | None = None


def _session_store() -> SessionStore:
    return SessionStore(get_store().artifacts_dir)


def _snapshot(session_id: str, session: RunSession) -> DebugSessionSnapshot:
    run = session.run
    status: Literal["paused", "success", "failed"] = (
        run.status if run.status in ("success", "failed") else "paused"
    )
    planned = session.planned_steps()
    return DebugSessionSnapshot(
        session_id=session_id,
        flow_name=run.flow_name,
        status=status,
        index=session.index,
        total_steps=len(planned),
        run_id=run.run_id,
        steps=[DebugStepInfo(**info) for info in planned],
        results=run.steps,
        hook_results=run.hook_results,
        error=run.error,
    )


def _load_state(store: SessionStore, session_id: str) -> dict[str, Any]:
    try:
        return store.get(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="debug session not found") from e


def _restore(state: dict[str, Any]) -> RunSession:
    return RunSession.from_state(get_registry(), get_store(), state)


@router.post("/debug/sessions", response_model=DebugSessionSnapshot)
def create_session(req: CreateSessionRequest) -> DebugSessionSnapshot:
    try:
        flow = load_flow_spec_from_yaml_text(req.flow_yaml)
    except FlowLoadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    store = _session_store()
    session = RunSession.start(
        get_registry(),
        get_store(),
        flow,
        input=req.input,
        vars=req.vars,
        request={"flow_yaml": req.flow_yaml, "input": req.input, "vars": req.vars},
    )
    session_id = session.run.run_id
    store.save(session_id, session.to_state())
    return _snapshot(session_id, session)


@router.get("/debug/sessions/{session_id}", response_model=DebugSessionSnapshot)
def get_session(session_id: str) -> DebugSessionSnapshot:
    store = _session_store()
    session = _restore(_load_state(store, session_id))
    return _snapshot(session_id, session)


@router.post("/debug/sessions/{session_id}/step", response_model=DebugSessionSnapshot)
def step_session(session_id: str) -> DebugSessionSnapshot:
    store = _session_store()
    with store.locked(session_id):
        session = _restore(_load_state(store, session_id))
        session.step()
        store.save(session_id, session.to_state())
    return _snapshot(session_id, session)


@router.post("/debug/sessions/{session_id}/run", response_model=DebugSessionSnapshot)
def run_session(session_id: str) -> DebugSessionSnapshot:
    store = _session_store()
    with store.locked(session_id):
        session = _restore(_load_state(store, session_id))
        session.run_to_completion()
        store.save(session_id, session.to_state())
    return _snapshot(session_id, session)


@router.delete("/debug/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    store = _session_store()
    with store.locked(session_id):
        session = _restore(_load_state(store, session_id))
        if session.run.status == "running":
            # 未完成的调试运行从历史中移除,避免遗留"运行中"
            get_store().delete_run(session_id)
        store.delete(session_id)
