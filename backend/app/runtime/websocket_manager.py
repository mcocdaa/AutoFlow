from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    _instance: WebSocketManager | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._connections: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}
        self._initialized = True

    def register_connection(self, conn_id: str, websocket: WebSocket) -> None:
        self._connections[conn_id] = websocket

    def unregister_connection(self, conn_id: str) -> None:
        if conn_id in self._connections:
            del self._connections[conn_id]
        for run_id in list(self._subscriptions.keys()):
            if conn_id in self._subscriptions[run_id]:
                self._subscriptions[run_id].remove(conn_id)
                if not self._subscriptions[run_id]:
                    del self._subscriptions[run_id]

    def subscribe(self, conn_id: str, run_id: str) -> None:
        if run_id not in self._subscriptions:
            self._subscriptions[run_id] = set()
        self._subscriptions[run_id].add(conn_id)

    def unsubscribe(self, conn_id: str, run_id: str) -> None:
        if run_id in self._subscriptions:
            if conn_id in self._subscriptions[run_id]:
                self._subscriptions[run_id].remove(conn_id)
                if not self._subscriptions[run_id]:
                    del self._subscriptions[run_id]

    async def broadcast_event(self, run_id: str, event_data: Dict[str, Any]) -> None:
        if run_id not in self._subscriptions:
            return
        conn_ids = list(self._subscriptions[run_id])
        for conn_id in conn_ids:
            if conn_id not in self._connections:
                continue
            websocket = self._connections[conn_id]
            try:
                await websocket.send_json(event_data)
            except WebSocketDisconnect:
                self.unregister_connection(conn_id)
            except Exception:
                self.unregister_connection(conn_id)


@lru_cache(maxsize=1)
def get_websocket_manager() -> WebSocketManager:
    return WebSocketManager()
