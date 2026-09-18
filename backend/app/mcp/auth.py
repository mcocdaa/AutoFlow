# @file /backend/app/mcp/auth.py
# @brief MCP 端点可选 Bearer token 校验(ASGI 中间件,仅拦截 /mcp)
# @create 2026-09-18

from __future__ import annotations

import hmac

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def _is_mcp_path(path: str) -> bool:
    return path == "/mcp" or path.startswith("/mcp/")


class MCPTokenMiddleware:
    """静态 token 校验:token 为空时不应挂载本中间件"""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _is_mcp_path(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        authorization = headers.get("authorization", "")
        expected = f"Bearer {self.token}"
        if not hmac.compare_digest(authorization, expected):
            response = JSONResponse(
                {"detail": "invalid mcp token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


__all__ = ["MCPTokenMiddleware"]
