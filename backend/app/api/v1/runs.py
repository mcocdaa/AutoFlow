# @file /backend/app/api/v1/routes/runs.py
# @brief 执行与查询 Run 的最小接口
# @create 2026-02-21 00:00:00

from __future__ import annotations

from typing import Any

from app.runtime import get_runner, get_store
from app.runtime.loaders import FlowLoadError, load_flow_spec_from_yaml_text
from app.runtime.models import RunResult
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

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


@router.get("/runs/{run_id}/artifacts/{file_path:path}")
def download_artifact(run_id: str, file_path: str) -> FileResponse:
    """Serve an artifact file from a run's artifacts directory.

    The file_path is resolved relative to the run's artifacts sub-directory
    and validated against path-traversal attacks.
    """
    store = get_store()
    try:
        store.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="run not found") from e

    run_artifacts_dir = store.artifacts_dir / run_id
    resolved = (run_artifacts_dir / file_path).resolve()

    # Prevent path traversal: the resolved path MUST be inside the run's dir
    try:
        resolved.relative_to(run_artifacts_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="path traversal denied") from None

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")

    return FileResponse(resolved)


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str) -> None:
    """Delete a run and its artifacts directory."""
    store = get_store()
    try:
        store.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="run not found") from e
    store.delete_run(run_id)
