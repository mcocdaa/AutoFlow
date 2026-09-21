# @file /backend/app/mcp/server.py
# @brief MCP Server 构建/挂载:MCPServer 工具注册、路由注入、lifespan 组装
# @create 2026-09-18

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from app.core.registry import Registry
from app.mcp.auth import MCPTokenMiddleware
from app.mcp.tools import (
    McpDeps,
    get_artifact,
    get_flow,
    get_run,
    get_run_diff,
    list_capabilities,
    list_flows,
    list_runs,
    replay_run_sync,
    run_flow_sync,
    search_flow_hub,
    start_replay_async,
    start_run_async,
    time_travel_run,
    validate_flow,
)
from app.runtime.runner import Runner
from app.runtime.storage.store import RunStore
from fastapi import FastAPI

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"

INSTRUCTIONS = (
    "AutoFlow 是自动化（RPA）执行引擎：Flow 由步骤（Action + 可选 Check）组成，"
    "每次执行产生可查询、可回放、带产物的运行记录。"
    "先用 list_capabilities/list_flows 发现能力与可用流程，再 run_flow 执行；"
    "长流程可用 wait=false 后以 get_run 轮询，失败或需要对比时用 replay_run。"
)


@dataclass
class MCPBinding:
    """MCP 与 FastAPI 的绑定:路由 + 会话管理器 lifespan + 可选 token"""

    server: MCPServer
    routes: list[Any] = field(default_factory=list)
    token: str = ""

    @asynccontextmanager
    async def lifespan(self, _: Any = None) -> AsyncIterator[None]:
        """兼容 Starlette 传入 app 参数的 lifespan 协议"""
        async with self.server.session_manager.run():
            yield


def create_mcp_binding(
    registry: Registry,
    store: RunStore,
    runner: Runner,
    *,
    flows_dir: Path,
    token: str = "",
    version: str = "",
    name: str = "AutoFlow",
) -> MCPBinding:
    """构建 MCPServer 并注册全部工具(调用方保证 enabled)"""
    deps = McpDeps(
        registry=registry,
        store=store,
        runner=runner,
        flows_dir=flows_dir,
    )
    server = MCPServer(name=name, version=version, instructions=INSTRUCTIONS)

    @server.tool(
        name="list_capabilities",
        description="列出已加载插件、已注册 Action/Check 及插件加载错误",
    )
    async def list_capabilities_tool() -> dict[str, Any]:
        return list_capabilities(deps)

    @server.tool(
        name="list_flows",
        description="列出 flows/ 内可用 Flow（name/description/steps）与无法解析的文件",
    )
    async def list_flows_tool() -> dict[str, Any]:
        return await anyio.to_thread.run_sync(list_flows, deps)

    @server.tool(
        name="run_flow",
        description=(
            "执行 Flow：提供 flow_name（flows/ 目录内）或 flow_yaml（内联 YAML）之一。"
            "wait=true 阻塞返回 RunResult；wait=false 立即返回 run_id，用 get_run 轮询"
        ),
    )
    async def run_flow_tool(
        flow_name: str | None = None,
        flow_yaml: str | None = None,
        input: Any = None,
        vars: dict[str, Any] | None = None,
        wait: bool = True,
    ) -> dict[str, Any]:
        kwargs = {
            "flow_name": flow_name,
            "flow_yaml": flow_yaml,
            "input": input,
            "vars": vars,
        }
        if wait:
            return await anyio.to_thread.run_sync(lambda: run_flow_sync(deps, **kwargs))
        return start_run_async(deps, **kwargs)

    @server.tool(
        name="get_run",
        description="按 run_id 查询运行状态与结果（运行中可见已完成步骤）",
    )
    async def get_run_tool(run_id: str) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(get_run, deps, run_id)

    @server.tool(
        name="list_runs",
        description="按开始时间倒序列出最近运行（默认 20 条）",
    )
    async def list_runs_tool(limit: int = 20) -> list[dict[str, Any]]:
        return await anyio.to_thread.run_sync(list_runs, deps, limit)

    @server.tool(
        name="replay_run",
        description="重放某次运行保存的请求，生成新的运行；wait 语义同 run_flow",
    )
    async def replay_run_tool(run_id: str, wait: bool = True) -> dict[str, Any]:
        if wait:
            return await anyio.to_thread.run_sync(replay_run_sync, deps, run_id)
        return start_replay_async(deps, run_id)

    @server.tool(
        name="get_artifact",
        description=(
            "读取运行产物文本（大输出以 __artifact__ 索引引用）。"
            "超出 max_bytes 截断并置 truncated=true"
        ),
    )
    async def get_artifact_tool(
        run_id: str,
        path: str,
        max_bytes: int = 262144,
    ) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(
            get_artifact, deps, run_id, path, max_bytes
        )

    @server.tool(
        name="get_flow",
        description="查看指定 Flow 的 YAML 源码、步骤结构及说明",
    )
    async def get_flow_tool(flow_name: str) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(get_flow, deps, flow_name)

    @server.tool(
        name="validate_flow",
        description="校验 Flow YAML 语法与步骤结构有效性",
    )
    async def validate_flow_tool(flow_yaml: str) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(validate_flow, deps, flow_yaml)

    @server.tool(
        name="time_travel_run",
        description=(
            "时间旅行单步回放工具：从指定历史运行(run_id)的某一步骤(step_index)分叉重跑。"
            "run_to_completion=true 执行到底返回完整结果；run_to_completion=false 执行单步调试"
        ),
    )
    async def time_travel_run_tool(
        run_id: str,
        step_index: int,
        run_to_completion: bool = True,
    ) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(
            time_travel_run, deps, run_id, step_index, run_to_completion
        )

    @server.tool(
        name="get_run_diff",
        description="对比两次运行（如原始运行 vs 分叉重跑）在步骤状态、Check 断言及输出上的细粒度差异",
    )
    async def get_run_diff_tool(run_id_a: str, run_id_b: str) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(get_run_diff, deps, run_id_a, run_id_b)

    @server.tool(
        name="search_flow_hub",
        description="检索 Flow Hub 流程市场上的精选开箱即用流程模板（SRE自愈、采集研报、安全调用链等）",
    )
    async def search_flow_hub_tool(
        category: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return await anyio.to_thread.run_sync(search_flow_hub, category, query)

    transport = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
        transport_security=transport,
    )
    return MCPBinding(server=server, routes=list(mcp_app.routes), token=token)


def install_mcp(app: FastAPI, binding: MCPBinding) -> None:
    """把 MCP 路由注入 FastAPI(须在静态资源兜底挂载之前),按需加 token 中间件"""
    app.router.routes.extend(binding.routes)
    if binding.token:
        app.add_middleware(MCPTokenMiddleware, token=binding.token)
    logger.info("MCP server mounted at %s", MCP_PATH)


__all__ = ["MCP_PATH", "MCPBinding", "create_mcp_binding", "install_mcp"]
