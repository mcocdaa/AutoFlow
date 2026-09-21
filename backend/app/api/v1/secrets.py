# @file /backend/app/api/v1/secrets.py
# @brief 本地敏感凭据保密柜 API
# @create 2026-09-20

from __future__ import annotations

from typing import Any

from app.core.secrets_vault import get_secrets_vault
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class SetSecretRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    value: str = Field(..., min_length=1)


class SecretItem(BaseModel):
    key: str
    masked_value: str


@router.get("/secrets", response_model=list[SecretItem])
def list_secrets() -> list[dict[str, str]]:
    """列出保密柜中的凭据（值脱敏）"""
    vault = get_secrets_vault()
    return vault.list_secrets()


@router.post("/secrets", status_code=200)
def set_secret(req: SetSecretRequest) -> dict[str, Any]:
    """设置或更新凭据"""
    vault = get_secrets_vault()
    vault.set_secret(req.key, req.value)
    return {"status": "ok", "key": req.key}


@router.delete("/secrets/{key}", status_code=200)
def delete_secret(key: str) -> dict[str, Any]:
    """删除凭据"""
    vault = get_secrets_vault()
    deleted = vault.delete_secret(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="secret not found")
    return {"status": "ok", "deleted": True}
