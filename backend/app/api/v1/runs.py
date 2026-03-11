# @file /backend/app/api/v1/routes/runs.py
# @brief 执行与查询 Run 的最小接口
# @create 2026-02-21 00:00:00

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.runtime.flow_loader import FlowLoadError, load_flow_spec_from_yaml_text
from app.runtime.models import RunResult
from app.runtime.runtime import get_runner, get_store

router = APIRouter()


class ExecuteFlowRequest(BaseModel):
    flow_yaml: str
    input: Any | None = None
    vars: dict[str, Any] = Field(default_factory=dict)


@router.post("/runs/execute", response_model=RunResult)
def execute_flow(req: ExecuteFlowRequest) -> RunResult:
    try:
        flow = load_flow_spec_from_yaml_text(req.flow_yaml)
    except FlowLoadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    runner = get_runner()
    return runner.run_flow(flow, input=req.input, vars=req.vars)


@router.get("/runs", response_model=list[RunResult])
def list_runs() -> list[RunResult]:
    store = get_store()
    return store.list_runs()


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    store = get_store()
    try:
        return store.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="run not found") from e

