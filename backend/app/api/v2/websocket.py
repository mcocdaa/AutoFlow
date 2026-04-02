# @file /backend/app/api/v2/websocket.py
# @brief WebSocket API
# @create 2026-04-02

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.runtime.websocket_manager import get_websocket_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，处理连接、消息和断开连接"""
    conn_id = str(uuid.uuid4())
    manager = get_websocket_manager()

    await websocket.accept()
    await manager.register_connection(conn_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                run_id = message.get("run_id")

                if message_type == "subscribe" and run_id:
                    manager.subscribe(conn_id, run_id)
                elif message_type == "unsubscribe" and run_id:
                    manager.unsubscribe(conn_id, run_id)
            except json.JSONDecodeError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.unregister_connection(conn_id)
