from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.database_manager import database_manager
from app.runtime.models import WorkflowSpec


class WorkflowStore:
    """工作流存储 - 使用 SQLAlchemy 持久化"""

    def __init__(self):
        pass

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return next(database_manager.get_db())

    def save_workflow(
        self,
        name: str,
        yaml: str,
        nodes: List[dict],
        edges: List[dict],
        description: str | None = None,
        workflow_id: str | None = None,
    ) -> WorkflowSpec:
        """保存工作流

        Args:
            name: 工作流名称
            yaml: 工作流 YAML 内容
            nodes: 节点列表
            edges: 连线列表
            description: 工作流描述（可选）
            workflow_id: 工作流 ID，如果提供则更新现有工作流

        Returns:
            WorkflowSpec: 保存的工作流对象
        """
        session = self._get_session()
        try:
            if workflow_id:
                workflow = (
                    session.query(WorkflowSpec)
                    .filter(WorkflowSpec.id == workflow_id)
                    .first()
                )
                if workflow:
                    workflow.name = name
                    workflow.description = description
                    workflow.nodes = nodes
                    workflow.edges = edges
                    workflow.yaml = yaml
                else:
                    workflow = WorkflowSpec(
                        id=workflow_id,
                        name=name,
                        description=description,
                        nodes=nodes,
                        edges=edges,
                        yaml=yaml,
                    )
                    session.add(workflow)
            else:
                workflow = WorkflowSpec(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description,
                    nodes=nodes,
                    edges=edges,
                    yaml=yaml,
                )
                session.add(workflow)
            session.commit()
            session.refresh(workflow)
            return workflow
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_workflow(self, workflow_id: str) -> WorkflowSpec | None:
        """通过 ID 获取工作流"""
        session = self._get_session()
        try:
            return (
                session.query(WorkflowSpec)
                .filter(WorkflowSpec.id == workflow_id)
                .first()
            )
        finally:
            session.close()

    def list_workflows(
        self,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> List[WorkflowSpec]:
        """获取工作流列表（支持分页和搜索）

        Args:
            page: 页码（默认 1）
            page_size: 每页数量（默认 20）
            search: 搜索关键词（可选）

        Returns:
            List[WorkflowSpec]: 工作流列表
        """
        session = self._get_session()
        try:
            query = session.query(WorkflowSpec)

            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (WorkflowSpec.name.ilike(search_pattern))
                    | (WorkflowSpec.description.ilike(search_pattern))
                )

            query = query.order_by(WorkflowSpec.updated_at.desc())

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

    def count_workflows(self, search: str | None = None) -> int:
        """统计工作流总数（支持搜索）

        Args:
            search: 搜索关键词（可选）

        Returns:
            int: 工作流总数
        """
        session = self._get_session()
        try:
            query = session.query(WorkflowSpec)

            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (WorkflowSpec.name.ilike(search_pattern))
                    | (WorkflowSpec.description.ilike(search_pattern))
                )

            return query.count()
        finally:
            session.close()

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        session = self._get_session()
        try:
            workflow = (
                session.query(WorkflowSpec)
                .filter(WorkflowSpec.id == workflow_id)
                .first()
            )
            if workflow:
                session.delete(workflow)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
