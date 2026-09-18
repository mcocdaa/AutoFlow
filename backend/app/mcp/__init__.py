# @file /backend/app/mcp/__init__.py
# @brief MCP Server 模块入口(设计见 specs/2026-09-18-mcp-bridge-design.md)
# @create 2026-09-18

from app.mcp.server import MCPBinding, create_mcp_binding, install_mcp

__all__ = ["MCPBinding", "create_mcp_binding", "install_mcp"]
