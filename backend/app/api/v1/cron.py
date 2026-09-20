# @file /backend/app/api/v1/cron.py
# @brief 内置 Cron 引擎配置、查询与下次触发时间预测 API
# @create 2026-09-20

from __future__ import annotations

from typing import Any

from app.runtime.cron.scheduler import (
    get_cron_scheduler,
    predict_next_runs,
    validate_cron_expression,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ValidateCronRequest(BaseModel):
    expression: str = Field(..., description="Cron 表达式，如 */5 * * * *")
    count: int = Field(default=5, ge=1, le=20, description="预测未来触发次数")


class ValidateCronResponse(BaseModel):
    valid: bool
    expression: str
    next_runs: list[str] = Field(default_factory=list)
    error: str | None = None


class RegisterCronJobRequest(BaseModel):
    flow_name: str
    cron_expr: str
    job_id: str | None = None
    input: Any = None
    vars: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


@router.post("/cron/validate", response_model=ValidateCronResponse)
def validate_cron(req: ValidateCronRequest) -> ValidateCronResponse:
    """验证 Cron 表达式并返回未来若干次预测触发时间"""
    expr = req.expression.strip()
    if not validate_cron_expression(expr):
        return ValidateCronResponse(
            valid=False,
            expression=expr,
            error="无效的 Cron 表达式 (需符合标准 5 段或 6 段 cron 语法)",
        )

    try:
        times = predict_next_runs(expr, count=req.count)
        return ValidateCronResponse(valid=True, expression=expr, next_runs=times)
    except Exception as e:
        return ValidateCronResponse(valid=False, expression=expr, error=str(e))


@router.get("/cron/jobs")
def list_cron_jobs() -> list[dict[str, Any]]:
    """列出当前所有已注册的 Cron 任务状态"""
    scheduler = get_cron_scheduler()
    return scheduler.list_jobs()


@router.post("/cron/jobs")
def register_cron_job(req: RegisterCronJobRequest) -> dict[str, Any]:
    """注册或更新 Cron 调度任务"""
    scheduler = get_cron_scheduler()
    try:
        job = scheduler.register_job(
            flow_name=req.flow_name,
            cron_expr=req.cron_expr,
            job_id=req.job_id,
            input=req.input,
            vars=req.vars,
            enabled=req.enabled,
        )
        return {
            "status": "ok",
            "job_id": job.job_id,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/cron/jobs/{job_id}")
def delete_cron_job(job_id: str) -> dict[str, Any]:
    """删除 Cron 调度任务"""
    scheduler = get_cron_scheduler()
    removed = scheduler.unregister_job(job_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "ok", "deleted": True}


@router.post("/cron/jobs/{job_id}/run")
def run_cron_job_immediately(job_id: str) -> dict[str, Any]:
    """立即触发一次 Cron 任务"""
    scheduler = get_cron_scheduler()
    try:
        run_id = scheduler.trigger_job_now(job_id)
        return {"status": "triggered", "run_id": run_id}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
