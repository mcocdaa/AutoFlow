# @file /backend/app/api/v2/workflows.py
# @brief V2 版本工作流 CRUD API
# @create 2026-04-02

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.runtime import get_workflow_store
from app.runtime.models import (
    V2SuccessResponse,
    V2WorkflowCreateRequest,
    V2WorkflowListItem,
    V2WorkflowListResponse,
    V2WorkflowResponse,
    V2WorkflowUpdateRequest,
)
from app.runtime.yaml_loader import YAMLLoader, YAMLLoaderError

router = APIRouter()


@router.post("/workflows", response_model=V2WorkflowResponse)
def create_workflow(req: V2WorkflowCreateRequest) -> V2WorkflowResponse:
    """创建新工作流（V2 版本）"""
    try:
        YAMLLoader.load(req.yaml)
    except YAMLLoaderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    store = get_workflow_store()
    workflow = store.save_workflow(
        name=req.name,
        description=req.description,
        yaml=req.yaml,
        nodes=[],
        edges=[],
    )
    return V2WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        yaml=workflow.yaml,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.get("/workflows", response_model=V2WorkflowListResponse)
def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
) -> V2WorkflowListResponse:
    """获取工作流列表（V2 版本，支持分页和搜索）"""
    store = get_workflow_store()
    workflows = store.list_workflows(page=page, page_size=page_size, search=search)
    total = store.count_workflows(search=search)

    return V2WorkflowListResponse(
        workflows=[
            V2WorkflowListItem(
                id=w.id,
                name=w.name,
                description=w.description,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in workflows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/workflows/{workflow_id}", response_model=V2WorkflowResponse)
def get_workflow(workflow_id: str) -> V2WorkflowResponse:
    """获取指定工作流详情（V2 版本）"""
    store = get_workflow_store()
    workflow = store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")
    return V2WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        yaml=workflow.yaml,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.put("/workflows/{workflow_id}", response_model=V2WorkflowResponse)
def update_workflow(
    workflow_id: str, req: V2WorkflowUpdateRequest
) -> V2WorkflowResponse:
    """更新工作流（V2 版本）"""
    store = get_workflow_store()
    existing_workflow = store.get_workflow(workflow_id)
    if not existing_workflow:
        raise HTTPException(status_code=404, detail="workflow not found")

    name = req.name if req.name is not None else existing_workflow.name
    description = (
        req.description
        if req.description is not None
        else existing_workflow.description
    )
    yaml = req.yaml if req.yaml is not None else existing_workflow.yaml

    if req.yaml is not None:
        try:
            YAMLLoader.load(req.yaml)
        except YAMLLoaderError as e:
            raise HTTPException(status_code=400, detail=str(e))

    workflow = store.save_workflow(
        name=name,
        description=description,
        yaml=yaml,
        nodes=[],
        edges=[],
        workflow_id=workflow_id,
    )
    return V2WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        yaml=workflow.yaml,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.delete("/workflows/{workflow_id}", response_model=V2SuccessResponse)
def delete_workflow(workflow_id: str) -> V2SuccessResponse:
    """删除工作流（V2 版本）"""
    store = get_workflow_store()
    success = store.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="workflow not found")
    return V2SuccessResponse(success=True)
