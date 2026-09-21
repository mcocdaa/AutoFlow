# @file /backend/app/runtime/cron/scheduler.py
# @brief 基于 croniter 的内置 Cron 定时调度引擎
# @create 2026-09-20

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.mcp.flows import resolve_flow, scan_flows
from app.runtime import get_registry, get_store
from app.runtime.loaders import load_flow_spec_from_yaml_text
from app.runtime.session import RunSession
from croniter import croniter

logger = logging.getLogger(__name__)


@dataclass
class CronJob:
    job_id: str
    flow_name: str
    cron_expr: str
    enabled: bool = True
    input: Any = None
    vars: dict[str, Any] | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_run_id: str | None = None
    last_status: str | None = None


def validate_cron_expression(expr: str) -> bool:
    """验证 Cron 表达式是否合法"""
    return croniter.is_valid(expr)


def predict_next_runs(
    expr: str,
    count: int = 5,
    base_time: datetime | None = None,
) -> list[str]:
    """预测接下来的 N 次触发时间 (ISO 8601 格式)"""
    if not validate_cron_expression(expr):
        raise ValueError(f"Invalid cron expression: {expr}")

    base = base_time or datetime.now(UTC)
    itr = croniter(expr, base)
    times: list[str] = []
    for _ in range(count):
        next_dt: datetime = itr.get_next(datetime)
        if next_dt.tzinfo is None:
            next_dt = next_dt.replace(tzinfo=UTC)
        times.append(next_dt.isoformat())
    return times


class CronScheduler:
    """轻量协程 Cron 调度引擎"""

    def __init__(self, flows_dir: Path) -> None:
        self.flows_dir = flows_dir
        self.jobs: dict[str, CronJob] = {}
        self._lock = threading.Lock()

    def register_job(
        self,
        flow_name: str,
        cron_expr: str,
        job_id: str | None = None,
        input: Any = None,
        vars: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> CronJob:
        """注册或更新 Cron 调度任务"""
        if not validate_cron_expression(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        jid = job_id or f"cron_{flow_name}"
        now = datetime.now(UTC)
        itr = croniter(cron_expr, now)
        next_dt: datetime = itr.get_next(datetime)
        if next_dt.tzinfo is None:
            next_dt = next_dt.replace(tzinfo=UTC)

        job = CronJob(
            job_id=jid,
            flow_name=flow_name,
            cron_expr=cron_expr,
            enabled=enabled,
            input=input,
            vars=vars,
            next_run_at=next_dt,
        )
        with self._lock:
            self.jobs[jid] = job
        logger.info(
            "Cron job '%s' registered for flow '%s', next run: %s",
            jid,
            flow_name,
            next_dt,
        )
        return job

    def unregister_job(self, job_id: str) -> bool:
        """注销任务"""
        with self._lock:
            return self.jobs.pop(job_id, None) is not None

    def list_jobs(self) -> list[dict[str, Any]]:
        """列出所有调度任务状态"""
        with self._lock:
            result = []
            for j in self.jobs.values():
                d = asdict(j)
                d["next_run_at"] = j.next_run_at.isoformat() if j.next_run_at else None
                d["last_run_at"] = j.last_run_at.isoformat() if j.last_run_at else None
                result.append(d)
            return result

    def scan_and_sync_flows(self) -> None:
        """扫描 flows/ 目录，自动同步 Flow 顶层定义的 cron 配置"""
        if not self.flows_dir.is_dir():
            return
        entries = scan_flows(self.flows_dir)
        for entry in entries:
            if "error" in entry:
                continue
            name = entry.get("name")
            if not name:
                continue
            try:
                _, flow_yaml = resolve_flow(self.flows_dir, name)
                flow = load_flow_spec_from_yaml_text(flow_yaml)
                cron_val: str | None = None
                if hasattr(flow, "cron") and flow.cron:
                    cron_val = flow.cron
                elif hasattr(flow, "trigger") and flow.trigger:
                    cron_val = getattr(flow.trigger, "cron", None)

                jid = f"flow_file_{name}"
                if cron_val and validate_cron_expression(cron_val):
                    if jid not in self.jobs:
                        self.register_job(name, cron_val, job_id=jid)
                elif jid in self.jobs:
                    # 原来配置了 cron 但现在移除了
                    self.unregister_job(jid)
            except Exception as e:
                logger.debug("Failed checking flow '%s' for cron: %s", name, e)

    def trigger_job_now(self, job_id: str) -> str:
        """手动立即触发一次指定任务，返回 run_id"""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError(f"Job '{job_id}' not found")

        return self._execute_job(job)

    def _execute_job(self, job: CronJob) -> str:
        """执行 Flow 任务"""
        _, flow_yaml = resolve_flow(self.flows_dir, job.flow_name)
        flow = load_flow_spec_from_yaml_text(flow_yaml)

        req_record = {
            "flow_yaml": flow_yaml,
            "input": job.input,
            "vars": job.vars or {},
            "trigger": "cron",
            "job_id": job.job_id,
        }

        registry = get_registry()
        store = get_store()
        session = RunSession.start(
            registry,
            store,
            flow,
            input=job.input,
            vars=job.vars,
            request=req_record,
        )

        run_id = session.run.run_id
        job.last_run_at = datetime.now(UTC)
        job.last_run_id = run_id

        def _run_in_thread():
            try:
                res = session.run_to_completion()
                job.last_status = res.status
            except Exception as e:
                logger.exception("Cron flow execution failed: %s", e)
                job.last_status = "failed"

        t = threading.Thread(
            target=_run_in_thread, name=f"cron-{job.job_id}-{run_id[:8]}", daemon=True
        )
        t.start()
        return run_id

    async def start_scheduler_loop(
        self,
        stop_event: asyncio.Event | None = None,
        check_interval_seconds: float = 2.0,
    ) -> None:
        """后台异步协程调度循环"""
        logger.info("CronScheduler loop started (tick=%.1fs)", check_interval_seconds)
        self.scan_and_sync_flows()

        while True:
            try:
                now = datetime.now(UTC)
                with self._lock:
                    jobs_to_run: list[CronJob] = []
                    for job in list(self.jobs.values()):
                        if not job.enabled or not job.next_run_at:
                            continue
                        if now >= job.next_run_at:
                            jobs_to_run.append(job)
                            # 计算下次运行时间
                            itr = croniter(job.cron_expr, now)
                            next_dt = itr.get_next(datetime)
                            if next_dt.tzinfo is None:
                                next_dt = next_dt.replace(tzinfo=UTC)
                            job.next_run_at = next_dt

                for job in jobs_to_run:
                    try:
                        logger.info(
                            "Cron trigger due for '%s' (flow='%s')",
                            job.job_id,
                            job.flow_name,
                        )
                        self._execute_job(job)
                    except Exception as e:
                        logger.exception(
                            "CronScheduler failed triggering '%s': %s", job.job_id, e
                        )

            except Exception as e:
                logger.exception("Unexpected error in CronScheduler loop: %s", e)

            if stop_event is not None:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=check_interval_seconds
                    )
                    logger.info("CronScheduler loop stopped via stop_event.")
                    break
                except TimeoutError:
                    pass
            else:
                await asyncio.sleep(check_interval_seconds)


_scheduler_instance: CronScheduler | None = None


def get_cron_scheduler() -> CronScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        from app.core.setting_manager import setting_manager

        flows_dir = Path(setting_manager.FLOWS_DIR)
        _scheduler_instance = CronScheduler(flows_dir)
    return _scheduler_instance
