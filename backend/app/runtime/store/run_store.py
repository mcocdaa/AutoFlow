from __future__ import annotations

import datetime
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.database_manager import database_manager
from app.runtime.models import RunSpec

logger = logging.getLogger(__name__)


class RunStore:
    """执行记录存储 - 使用 SQLAlchemy 持久化"""

    def __init__(self):
        pass

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return next(database_manager.get_db())

    def save_run(
        self,
        run_id: str,
        workflow_id: str,
        inputs: dict,
        node_states: dict,
        status: str = "pending",
        started_at: datetime.datetime | None = None,
        finished_at: datetime.datetime | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> RunSpec:
        """保存执行记录

        Args:
            run_id: 执行 ID
            workflow_id: 工作流 ID
            inputs: 输入参数
            node_states: 节点状态
            status: 执行状态
            started_at: 开始时间
            finished_at: 结束时间
            duration_ms: 持续时间
            error: 错误信息

        Returns:
            RunSpec: 保存的执行记录对象
        """
        session = self._get_session()
        try:
            run = session.query(RunSpec).filter(RunSpec.id == run_id).first()
            if run:
                run.workflow_id = workflow_id
                run.status = status
                run.inputs = inputs
                run.node_states = node_states
                run.started_at = started_at
                run.finished_at = finished_at
                run.duration_ms = duration_ms
                run.error = error
            else:
                run = RunSpec(
                    id=run_id,
                    workflow_id=workflow_id,
                    status=status,
                    inputs=inputs,
                    node_states=node_states,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    error=error,
                )
                session.add(run)
            session.commit()
            session.refresh(run)
            return run
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_run(self, run_id: str) -> RunSpec | None:
        """通过 ID 获取执行记录"""
        session = self._get_session()
        try:
            return session.query(RunSpec).filter(RunSpec.id == run_id).first()
        finally:
            session.close()

    def list_runs(
        self,
        page: int | None = None,
        page_size: int | None = None,
        workflow_id: str | None = None,
        status: str | None = None,
    ) -> List[RunSpec]:
        """获取执行记录列表（支持分页和过滤）

        Args:
            page: 页码（默认 1）
            page_size: 每页数量（默认 20）
            workflow_id: 按工作流 ID 过滤（可选）
            status: 按状态过滤（可选）

        Returns:
            List[RunSpec]: 执行记录列表
        """
        session = self._get_session()
        try:
            query = session.query(RunSpec)

            if workflow_id:
                query = query.filter(RunSpec.workflow_id == workflow_id)

            if status:
                query = query.filter(RunSpec.status == status)

            query = query.order_by(RunSpec.started_at.desc())

            if page is None and page_size is None:
                return query.all()
            else:
                if page is None:
                    page = 1
                if page_size is None:
                    page_size = 20
                offset = (page - 1) * page_size
                return query.offset(offset).limit(page_size).all()
        finally:
            session.close()

    def count_runs(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
    ) -> int:
        """统计执行记录总数（支持过滤）

        Args:
            workflow_id: 按工作流 ID 过滤（可选）
            status: 按状态过滤（可选）

        Returns:
            int: 执行记录总数
        """
        session = self._get_session()
        try:
            query = session.query(RunSpec)

            if workflow_id:
                query = query.filter(RunSpec.workflow_id == workflow_id)

            if status:
                query = query.filter(RunSpec.status == status)

            return query.count()
        finally:
            session.close()

    def update_run_status(
        self,
        run_id: str,
        status: str,
        started_at: datetime.datetime | None = None,
        finished_at: datetime.datetime | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> RunSpec | None:
        """更新执行状态和时间

        Args:
            run_id: 执行 ID
            status: 新的执行状态
            started_at: 开始时间（可选）
            finished_at: 结束时间（可选）
            duration_ms: 持续时间（可选）
            error: 错误信息（可选）

        Returns:
            RunSpec | None: 更新后的执行记录对象
        """
        session = self._get_session()
        try:
            run = session.query(RunSpec).filter(RunSpec.id == run_id).first()
            if run:
                run.status = status
                if started_at is not None:
                    run.started_at = started_at
                if finished_at is not None:
                    run.finished_at = finished_at
                if duration_ms is not None:
                    run.duration_ms = duration_ms
                if error is not None:
                    run.error = error
                session.commit()
                session.refresh(run)
                return run
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_node_state(
        self,
        run_id: str,
        node_id: str,
        node_state: dict,
    ) -> RunSpec | None:
        """更新节点状态

        Args:
            run_id: 执行 ID
            node_id: 节点 ID
            node_state: 节点状态对象

        Returns:
            RunSpec | None: 更新后的执行记录对象
        """
        session = self._get_session()
        try:
            run = session.query(RunSpec).filter(RunSpec.id == run_id).first()
            if run:
                node_states = dict(run.node_states)
                node_states[node_id] = node_state
                run.node_states = node_states
                session.commit()
                session.refresh(run)
                return run
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_execution_state(self, run_id: str, state_data: dict | None) -> None:
        """持久化执行状态（available_inputs、history、waiting_node_id）"""
        session = self._get_session()
        try:
            run = session.query(RunSpec).filter(RunSpec.id == run_id).first()
            if run:
                run.execution_state = state_data
                session.commit()
            else:
                logger.warning("save_execution_state: run %s not found", run_id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_execution_state(self, run_id: str) -> dict | None:
        """读取已持久化的执行状态"""
        session = self._get_session()
        try:
            run = session.query(RunSpec).filter(RunSpec.id == run_id).first()
            if run:
                return run.execution_state
            return None
        finally:
            session.close()
