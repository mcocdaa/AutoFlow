# @file backend/app/api/v1/common.py
# @brief 健康检查等公共接口
# @create 2026-03-06 10:00:00

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}
