# @file /backend/app/api/v1/webhooks.py
# @brief Webhook 外部事件网关路由，支持 HMAC-SHA256 签名校验
# @create 2026-09-20

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.core.secrets_vault import get_secrets_vault
from app.core.setting_manager import setting_manager
from app.mcp.flows import resolve_flow
from app.runtime import get_registry, get_runner, get_store
from app.runtime.loaders import load_flow_spec_from_yaml_text
from app.runtime.session import RunSession
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_hmac_sha256(raw_body: bytes, secret: str, signature_header: str) -> bool:
    """校验 HMAC-SHA256 签名 (格式: sha256=<hex> 或纯 <hex>)"""
    sig = signature_header.strip()
    if sig.startswith("sha256="):
        sig = sig[7:]

    mac = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256)
    expected_hex = mac.hexdigest()
    return hmac.compare_digest(expected_hex.lower(), sig.lower())


def _resolve_webhook_secret(flow_name: str, expected_token_in_flow: str | None) -> str:
    """获取此 Flow 对应的 Webhook 密钥 (优先 flow 配置，其次保密柜，最后全局配置)"""
    if expected_token_in_flow:
        return expected_token_in_flow

    vault = get_secrets_vault()
    vault_token = vault.get_secret(f"webhook_{flow_name}") or vault.get_secret(
        "webhook_secret"
    )
    if vault_token:
        return vault_token

    return str(setting_manager.get("WEBHOOK_SECRET") or "")


@router.post("/webhooks/{flow_name}/{token}")
@router.get("/webhooks/{flow_name}/{token}")
async def trigger_webhook(
    flow_name: str,
    token: str,
    request: Request,
    wait: bool = Query(default=False),
) -> Response:
    """动态 Webhook 触发入口:

    1. 校验 URL Token 或 HMAC-SHA256 签名 (X-Hub-Signature-256 / X-Webhook-Signature)
    2. 将请求体作为 input 传入 Flow
    3. 支持 wait=false (异步触发并返回 run_id) 或 wait=true (同步等待执行结束)
    """
    flows_dir = Path(setting_manager.FLOWS_DIR)
    try:
        _, flow_yaml = resolve_flow(flows_dir, flow_name)
        flow = load_flow_spec_from_yaml_text(flow_yaml)
    except Exception as e:
        logger.warning("Webhook flow '%s' resolve failed: %s", flow_name, e)
        raise HTTPException(
            status_code=404, detail=f"flow not found: {flow_name}"
        ) from e

    # 提取 flow 自身可能声明的 token
    flow_token: str | None = None
    if hasattr(flow, "trigger") and flow.trigger:
        flow_token = getattr(flow.trigger, "webhook_token", None)

    expected_secret = _resolve_webhook_secret(flow_name, flow_token)

    # 读取原始 body
    raw_body = await request.body()

    # 1. 签名校验 (若客户端携带了签名头，必须通过 HMAC 验证)
    signature = (
        request.headers.get("x-hub-signature-256")
        or request.headers.get("x-webhook-signature")
        or request.headers.get("x-signature-256")
    )
    if signature:
        secret_for_sig = expected_secret or token
        if not _verify_hmac_sha256(raw_body, secret_for_sig, signature):
            logger.warning(
                "Webhook HMAC signature verification failed for '%s'", flow_name
            )
            raise HTTPException(status_code=401, detail="Invalid HMAC-SHA256 signature")
    elif expected_secret:
        # 如果配置了密钥但未传签名，URL 中的 token 必须与之匹配
        if not hmac.compare_digest(token, expected_secret):
            logger.warning("Webhook token mismatch for '%s'", flow_name)
            raise HTTPException(status_code=401, detail="Invalid webhook token")

    # 2. 解析请求体数据作为 input
    flow_input: Any = None
    if raw_body:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                flow_input = json.loads(raw_body.decode("utf-8"))
            except Exception:
                flow_input = raw_body.decode("utf-8", errors="replace")
        else:
            try:
                flow_input = json.loads(raw_body.decode("utf-8"))
            except Exception:
                flow_input = raw_body.decode("utf-8", errors="replace")
    elif request.query_params:
        flow_input = dict(request.query_params)

    vars_payload: dict[str, Any] = {
        "webhook_trigger": {
            "method": request.method,
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
        }
    }

    # 3. 执行流程
    if wait:
        runner = get_runner()
        req_record = {
            "flow_yaml": flow_yaml,
            "input": flow_input,
            "vars": vars_payload,
            "trigger": "webhook",
        }
        result = runner.run_flow(
            flow, input=flow_input, vars=vars_payload, request=req_record
        )
        return JSONResponse(status_code=200, content=result.model_dump(mode="json"))

    # 异步执行
    store = get_store()
    registry = get_registry()
    req_record = {
        "flow_yaml": flow_yaml,
        "input": flow_input,
        "vars": vars_payload,
        "trigger": "webhook",
    }
    session = RunSession.start(
        registry,
        store,
        flow,
        input=flow_input,
        vars=vars_payload,
        request=req_record,
    )
    thread = threading.Thread(
        target=session.run_to_completion,
        name=f"webhook-{flow.name}-{session.run.run_id[:8]}",
        daemon=True,
    )
    thread.start()

    return JSONResponse(
        status_code=202,
        content={
            "status": "triggered",
            "run_id": session.run.run_id,
            "flow_name": flow.name,
        },
    )
