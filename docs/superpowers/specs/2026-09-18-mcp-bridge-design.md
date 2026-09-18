# 设计:MCP / Agent 双向桥（第一期：MCP Server）

- 日期:2026-09-18
- 状态:草案(待批准)
- 前置:`v1.1.0`（调试/回放/可观测已发布），API 无认证、单镜像 4 worker
- 关联 OpenSpec 变更:`openspec/changes/mcp-bridge/`
- 路线图:`docs/roadmap.md` 第 3 节第 1 项（本期只做出向 MCP Server；反向 Agent-step 下期）

## 1. 背景与目标

AutoFlow 的定位是 **Agent 的确定性执行层**：Agent 能调度大量动作，但缺少审计、重试、产物与回放能力。把 Flow 以 MCP（Model Context Protocol）工具暴露后，任意支持 MCP 的 Agent（Claude Code/Desktop、Cursor 等）即可调用"有历史、有产物、可回放"的流程，而不是裸命令。

本期目标：

- 在现有 FastAPI 应用上提供 **Streamable HTTP MCP Server**（路径 `/mcp`），单镜像零新增端口；
- 暴露 **Flow 级工具 + 只读查询工具**：能力发现、Flow 列表、执行（同步/异步）、运行查询、回放、产物读取；
- Flow 来源：根目录 `flows/` 目录（发现式）+ `run_flow` 内联 YAML（AI 起草）；
- 可选 Bearer token（`MCP_TOKEN`），与现有无认证 API 的安全口径一致并文档化。

**范围约束**：

- 不引入反向 Agent-step（`openclaw.spawn_agent` 等），下期另行设计；
- 不做 Action 级工具（参数 schema 缺失，先以 Flow 为单元）；
- 不新增前端页面（MCP 为机器接口，文档说明即可）；
- 4 worker 部署下必须可用（工具无会话粘性）；
- 对现有 REST API 完全向后兼容。

## 2. 技术选型与验证结论

| 选型点 | 结论 | 依据 |
|---|---|---|
| SDK | PyPI `mcp` **2.2.0**（Python ≥3.10，pydantic ≥2.12） | 官方 SDK；`FastMCP` 在 2.x 更名为 `MCPServer`（`mcp.server.mcpserver`） |
| 传输 | Streamable HTTP，**stateless + json_response** | 4 worker 下无 session 粘性问题；纯 JSON-RPC 响应，curl 可回归 |
| 挂载 | 取 `streamable_http_app()` 的路由**直接注入** FastAPI router | 已验证：`Mount` 会产生 `/mcp → /mcp/` 307 重定向且吞掉子应用 lifespan |
| 生命周期 | FastAPI `lifespan` 中 `async with mcp.session_manager.run()` | 子应用 lifespan 不会随 `Mount` 执行；必须由根应用托管 |
| 安全 | 自实现 ASGI Bearer 中间件，仅拦截 `/mcp` 路径 | SDK 的 `RequireAuthMiddleware` 依赖 `AuthenticationMiddleware`，配置链路复杂且对可选 token 场景过重 |
| DNS 防重绑定 | 关闭 | 服务面向本机/内网，非浏览器同源场景；token 可选 |

已用 spike 验证：`initialize` → `tools/list` → `tools/call` 全链路 200，无需 `mcp-session-id`。

## 3. 模块设计

```
backend/app/mcp/
├── __init__.py      # 导出 create_mcp_binding / install_mcp
├── flows.py         # Flow 目录扫描与解析（名称解析、路径安全）
├── tools.py         # 工具实现（依赖注入 registry/store/runner，纯函数可单测）
├── auth.py          # MCPTokenMiddleware（ASGI，静态 token，constant-time 比较）
└── server.py        # MCPServer 构建、工具注册、路由注入、lifespan 组装
```

### 3.1 配置（`app/core/setting_manager.py`）

在 `_load_env` 的 `setdefault` 区块新增：

| 键 | 默认 | 说明 |
|---|---|---|
| `MCP_ENABLED` | `True`（truthy 解析） | 是否挂载 `/mcp` |
| `MCP_TOKEN` | `""` | 非空时 `/mcp` 要求 `Authorization: Bearer <token>` |
| `FLOWS_DIR` | `ROOT_DIR/flows` | Flow 目录；支持 `FLOWS_DIR` 环境变量覆盖 |

### 3.2 `flows.py`

- `scan_flows(flows_dir) -> list[FlowEntry]`：非递归扫描 `*.yaml`/`*.yml`；逐文件用 `load_flow_spec_from_yaml_text` 解析，成功返回 `{name, file, description, steps}`，失败返回 `{file, error}`（不抛）。
- `resolve_flow(flows_dir, flow_name) -> tuple[str, str]`（`(flow_name, yaml_text)`）：先按文件 stem 精确匹配，再按解析后的 `flow.name` 匹配；未命中抛 `ValueError` 并列出可用名称。
- 路径安全：只拼接 `flows_dir` 下文件名，不接受绝对路径/`..`；`run_flow(flow_yaml=...)` 是文本而非路径，无文件访问。

### 3.3 `tools.py`

工具函数统一以 `deps`（registry、store、flows_dir、runner）为主参数，注册时用闭包绑定，便于单测直接调用。

| 工具 | 入参 | 返回 | 语义 |
|---|---|---|---|
| `list_capabilities` | — | `{plugins, actions, checks, errors}` | 插件/动作/校验发现 |
| `list_flows` | — | `{flows: [...], errors: [...]}` | 目录内可用 Flow 与坏文件 |
| `run_flow` | `flow_name?`, `flow_yaml?`, `input?`, `vars?`, `wait=true` | `RunResult`（wait=true）或 `{run_id, status:"running"}`（false） | 必须二选一来源；内联 YAML 与文件统一落 `request.json` 供回放 |
| `get_run` | `run_id` | `RunResult` | 运行中可见部分步骤（每步落盘） |
| `list_runs` | `limit=20` | `[RunResult]` | 按开始时间倒序截断 |
| `replay_run` | `run_id`, `wait=true` | 同 `run_flow` | 重放已落盘请求；无请求时报错 |
| `get_artifact` | `run_id`, `path`, `max_bytes=262144` | `{path, text, truncated, size}` | 只读文本产物；`resolve()` + `is_relative_to` 防路径穿越 |

**执行模型**：

- `wait=true`：`anyio.to_thread.run_sync(runner.run_flow)`，避免阻塞 MCP 事件循环；
- `wait=false`：`RunSession.start(...)`（立即落 `run.json(status=running)` + `request.json`）后启动 `threading.Thread(daemon=True)` 跑 `run_to_completion()`，返回 `run_id`；Agent 用 `get_run` 轮询（每步已落盘）；
- 错误：工具内 `raise ValueError(中文消息)`，由 SDK 转为 `isError: true` 的工具结果（不中断连接）。

### 3.4 `server.py`

```python
def create_mcp_binding(registry, store, *, flows_dir, token) -> MCPBinding | None
def install_mcp(app, binding) -> None
```

- `create_mcp_binding`：构造 `MCPServer(name="AutoFlow", version=APP_VERSION, instructions=...)`，注册全部工具；调用 `streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True, transport_security=关闭 DNS 防重绑定)` 物化 `session_manager`；返回携带 `server`、`routes`、`token` 的绑定对象。
- `install_mcp`：把 `routes` 注入 `app.router.routes`（`/mcp` 精确路径，无重定向）；当 token 非空时 `app.add_middleware(MCPTokenMiddleware, token=token)`。
- lifespans：`create_mcp_binding` 返回的绑定提供 `lifespan()` 异步上下文；`main.py` 在创建 `FastAPI` 时组合（MCP 关闭则用 `None`）。

### 3.5 `auth.py`

- 纯 ASGI 中间件；`scope["type"] != "http"` 或路径不在 `/mcp` 下 → 直接透传（不影响 SPA/API）；
- 校验 `Authorization: Bearer <token>`（`hmac.compare_digest`）；
- 失败返回 `401` + `WWW-Authenticate: Bearer`，JSON `{"detail":"invalid mcp token"}`；
- token 为空（`MCP_TOKEN` 未配置）时不挂载该中间件。

### 3.6 `main.py` 集成

1. `binding = create_mcp_binding(...) if MCP_ENABLED else None`；
2. `FastAPI(..., lifespan=binding.lifespan if binding else None)`；
3. 现有 `register_routers(app)` 之后、静态资源 `app.mount("/", ...)` 之前 `install_mcp(app, binding)`（静态兜底路由必须最后）。

## 4. 安全与边界

- **认证**：`MCP_TOKEN` 可选；未设置时 `/mcp` 与现有 API 同等（无认证），README/docs 明确"勿公网暴露"；
- **执行面**：MCP 只是现有 `run_flow` 的另一个入口，不扩大权限面（同样可执行插件动作如 `openclaw.exec`）；
- **路径**：Flow 名称限定 `FLOWS_DIR`；`get_artifact` 限定该 run 产物目录且仅读文件；
- **输出体积**：产物读取默认上限 256 KiB（超出截断并标记）；
- **DoS 面**：`wait=false` 每次调用一个线程，无队列/并发限制；Trigger 运行时引入后再统一治理（文档标注）。

## 5. 测试与验证

**单测**（`backend/tests/test_mcp_tools.py`、`test_mcp_server.py`）：

1. `scan_flows`：合法/非法 YAML 混合目录 → 各自归位；`resolve_flow` 按 stem 与 `name` 命中、未命中含可用列表；
2. `run_flow` 内联 YAML 同步执行（dummy 动作）→ `success`，`request.json` 落盘，`replay_run` 生成新 `run_id`；
3. `wait=false` + 轮询 `get_run` → 最终 `success`；
4. `get_artifact`：正常读取、`truncated` 标记、`../` 穿越拒绝；
5. server 级：`TestClient` 走 `initialize`/`tools/list`/`tools/call`（含 token 401/200、非 `/mcp` 路径不受影响、MCP 关闭时 404）。

**回归**（`tools/test/feature-checks/run-checks.py` 新增 check 15）：

- `POST /mcp` initialize（`Accept: application/json, text/event-stream`）→ `serverInfo.name == "AutoFlow"`；
- `tools/list` 包含 `run_flow`/`get_run`/`replay_run`；
- `tools/call list_capabilities` 返回插件数 > 0。

**手工 E2E**：用官方 `mcp` 客户端（`streamablehttp_client`）连接本地/容器 `/mcp`，调用 `list_flows` → `run_flow` → `get_run`。

**基线**：当前 `pytest` 152 passed、容器回归 69/69；预期 ≥ 165 passed、回归 ≥ 74/74。

## 6. 依赖与构建

- `backend/pyproject.toml` 新增 `mcp = ">=2.2.0"`；`poetry.lock` 用容器内 `poetry==2.3.3` 重新生成（本机 poetry 环境损坏）；
- Dockerfile 新增 `COPY flows/ /app/flows/`（含 README 与示例 Flow）；
- `docker-compose.yml` 新增 `./flows:/app/flows:ro` 挂载（与 plugins 同为只读）；
- `.env.example` 新增 `MCP_ENABLED` / `MCP_TOKEN` / `FLOWS_DIR` 注释项。

## 7. 文档

- 新增 `docs/zh/modules/mcp.md`：端点、工具清单、鉴权、`flows/` 约定、异步轮询、客户端配置示例（Claude Code/Cursor JSON）、curl JSON-RPC 示例；
- `docs/zh/modules/index.md`、`README.md`（核心能力列表）、`docs/roadmap.md`（MCP 项标记第一期完成/反向待做）；
- `flows/README.md` + `flows/example.flow.yaml`（可直接 `run_flow(flow_name="example")`）。

## 8. 明确不做（本期）

- 反向 Agent-step（`openclaw.spawn_agent`、`openclaw.send_message` 等）；
- Action 级 MCP 工具与参数 schema；
- MCP resources/prompts 暴露（仅 tools）；
- 执行队列、并发限制、异步任务恢复（进程重启后 `running` 运行需人工处理，文档标注）；
- OAuth/OIDC（仅静态 Bearer token）。
