# @file /backend/app/api/v1/workflows.py
# @brief 工作流 CRUD API
# @create 2026-03-30

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.runtime import get_workflow_store
from app.runtime.models import (
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowSaveRequest,
)

router = APIRouter()


@router.post("/workflows", response_model=WorkflowResponse)
def create_workflow(req: WorkflowSaveRequest) -> WorkflowResponse:
    """创建新工作流"""
    store = get_workflow_store()
    workflow = store.save_workflow(
        name=req.name,
        description=req.description,
        nodes=req.nodes,
        edges=req.edges,
        yaml=req.yaml,
    )
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        yaml=workflow.yaml,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows() -> WorkflowListResponse:
    """获取所有工作流列表"""
    store = get_workflow_store()
    workflows = store.list_workflows()
    return WorkflowListResponse(
        workflows=[
            WorkflowResponse(
                id=w.id,
                name=w.name,
                description=w.description,
                nodes=w.nodes,
                edges=w.edges,
                yaml=w.yaml,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in workflows
        ]
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: str) -> WorkflowResponse:
    """获取指定工作流详情"""
    store = get_workflow_store()
    workflow = store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        yaml=workflow.yaml,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str) -> dict:
    """删除指定工作流"""
    store = get_workflow_store()
    success = store.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {"message": "workflow deleted successfully"}
