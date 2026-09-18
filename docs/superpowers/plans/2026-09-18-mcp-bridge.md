# MCP / Agent 双向桥（第一期）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 FastAPI 单镜像内挂载 `/mcp`（Streamable HTTP，stateless + JSON 响应），暴露 Flow 级与只读查询类 MCP 工具，让 Agent 可发现、执行、轮询、回放 AutoFlow 流程与读取产物；支持可选 Bearer token。

**Architecture:** 新增 `backend/app/mcp/` 模块（flows/tools/server/auth）；`main.py` 组合 lifespan 与路由注入（静态兜底挂载最后）；Flow 来源为 `flows/` 目录 + 内联 YAML；同步执行走线程池、异步执行用后台线程 + `run.json` 每步落盘支撑轮询。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / `mcp==2.2.0`（`MCPServer`，2.x 由 `FastMCP` 更名）；pytest；Docker 单镜像 4 worker。

**调研依据:** `docs/superpowers/specs/2026-09-18-mcp-bridge-design.md`；OpenSpec 变更 `openspec/changes/mcp-bridge/`。

**验证基线（实施前确认）:** `pytest` 152 passed；`ruff` 全绿；容器 `run-checks.sh` 69/69。

**分支策略:** 单分支 `feat/mcp-bridge`，一个 PR。

---

## Task 1: 依赖与配置

**Files:**
- Modify: `backend/pyproject.toml`（dependencies 新增 `mcp = ">=2.2.0"`）
- Regenerate: `backend/poetry.lock`
- Modify: `backend/app/core/setting_manager.py`（`MCP_ENABLED`/`MCP_TOKEN`/`FLOWS_DIR`）

- [ ] **Step 1: pyproject 增加依赖**

在 `[tool.poetry.dependencies]` 中 `pyyaml` 之后加：`mcp = ">=2.2.0"`。

- [ ] **Step 2: 容器内重生成 lock（本机 poetry 损坏）**

```bash
docker run --rm -v "$PWD/backend":/w -w /w python:3.12-slim \
  sh -c "pip install -q poetry==2.3.3 && poetry lock"
```

- [ ] **Step 3: setting_manager 默认值**

`_load_env` 的 `setdefault` 区块：

```python
self.config.setdefault("MCP_ENABLED", True)
self.config.setdefault("MCP_TOKEN", "")
self.config.setdefault("FLOWS_DIR", str(ROOT_DIR / "flows"))
self.config["MCP_ENABLED"] = _is_truthy(
    os.getenv("MCP_ENABLED", self.config["MCP_ENABLED"])
)
```

- [ ] **Step 4: 验证**

```bash
backend/.venv/bin/pip install -q mcp==2.2.0   # 本地 venv（uv 创建）
backend/.venv/bin/python -c "from mcp.server.mcpserver import MCPServer; print('ok')"
```

预期 `ok`。

---

## Task 2: Flow 目录发现（`app/mcp/flows.py`）

**Files:**
- Create: `backend/app/mcp/__init__.py`
- Create: `backend/app/mcp/flows.py`
- Test: `backend/tests/test_mcp_flows.py`

- [ ] **Step 1: 写失败测试**

`scan_flows`：tmp 目录放 `a.flow.yaml`（合法、`name: alpha`）、`b.yaml`（非法 YAML）、`note.txt`（忽略）→ 结果合法项 `file=a.flow.yaml, name=alpha`，错误项含 `b.yaml`；`resolve_flow("a")` 命中 stem、`resolve_flow("alpha")` 命中 name、`resolve_flow("missing")` 抛 `ValueError` 且消息含 `alpha`。

- [ ] **Step 2: 实现**

```python
def scan_flows(flows_dir: Path) -> list[dict]: ...
def resolve_flow(flows_dir: Path, flow_name: str) -> tuple[str, str]: ...
```

规则：非递归 `*.yaml`/`*.yml`（排序稳定）；解析用 `load_flow_spec_from_yaml_text`；`resolve_flow` 返回 `(flow.name, yaml_text)`；名称匹配先 stem 后 `flow.name`；目录不存在时 `scan_flows` 返回 `[]`。

- [ ] **Step 3: 运行** `backend/.venv/bin/python -m pytest tests/test_mcp_flows.py -q` → 全过。

---

## Task 3: 工具实现（`app/mcp/tools.py`）

**Files:**
- Create: `backend/app/mcp/tools.py`
- Test: `backend/tests/test_mcp_tools.py`

**接口（供 server 注册与学生成对测试）**

```python
@dataclass(frozen=True)
class McpDeps:
    registry: Registry
    store: RunStore
    runner: Runner
    flows_dir: Path


def list_capabilities(deps: McpDeps) -> dict: ...
def list_flows(deps: McpDeps) -> dict: ...
def run_flow(
    deps, *, flow_name=None, flow_yaml=None, input=None, vars=None, wait=True
) -> dict: ...
def get_run(deps, run_id: str) -> dict: ...
def list_runs(deps, limit: int = 20) -> list[dict]: ...
def replay_run(deps, run_id: str, wait: bool = True) -> dict: ...
def get_artifact(deps, run_id: str, path: str, max_bytes: int = 262144) -> dict: ...
```

- [ ] **Step 1: 写失败测试**（用既有 fixture 方式构造 `Registry`+tmp `RunStore`+`Runner`；动作使用内置/`dummy` 插件最小 Flow）

覆盖：内联 `run_flow` 成功 + `request.json` 存在；`replay_run` 新 `run_id`；`wait=False` 轮询至 `success`；`get_run` 未知 id 抛 `ValueError`；`get_artifact` 正常/截断/`../` 拒绝；`run_flow` 两个来源都缺或都给 → `ValueError`。

- [ ] **Step 2: 实现**

关键点：`wait=True` 用 `anyio.to_thread.run_sync`（工具函数为 async 包装，纯实现可同步，由 server 层适配）；`wait=False` 用 `RunSession.start` + `threading.Thread(daemon=True)`；`request` 统一为 `{"flow_yaml": text, "input": input, "vars": vars}`；返回 `RunResult.model_dump(mode="json")`。

- [ ] **Step 3: 运行** `pytest tests/test_mcp_tools.py -q` → 全过。

---

## Task 4: 服务与鉴权（`app/mcp/server.py`、`app/mcp/auth.py`、`main.py`）

**Files:**
- Create: `backend/app/mcp/auth.py`
- Create: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/__init__.py`（导出）
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_mcp_server.py`

- [ ] **Step 1: 写失败测试**

`TestClient` 场景：MCP 开启时 `initialize` 200 且 `serverInfo.name=="AutoFlow"`；`tools/list` 含 `run_flow`；`tools/call run_flow`（内联 dummy flow）`isError=false`；token 设置后无头 401、错误 401、正确 200，且 `/health` 不受影响；MCP 关闭时 `POST /mcp` 404。

- [ ] **Step 2: 实现 auth.py**

ASGI 中间件；仅路径 `== "/mcp"` 或 `startswith("/mcp/")` 且 `scope["type"]=="http"` 时校验；`hmac.compare_digest`；失败 401 + `WWW-Authenticate: Bearer` + JSON detail。

- [ ] **Step 3: 实现 server.py**

```python
def create_mcp_binding(registry, store, runner, *, enabled, token, flows_dir, version) -> MCPBinding | None
def install_mcp(app: FastAPI, binding: MCPBinding) -> None
```

- `MCPServer(name="AutoFlow", version=version, instructions="...")`；
- `@server.tool(...)` 注册 7 个工具；工具名与 docstring 使用中文说明；
- `streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True, transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))`；
- `MCPBinding` 持有 `routes`/`token`/`server`，提供 `lifespan()`（`async with server.session_manager.run()`）。

- [ ] **Step 4: main.py 集成**

按设计 3.6：binding 在 `FastAPI(...)` 之前创建；lifespan 组合；`install_mcp` 在 `register_routers` 之后、静态挂载之前。

- [ ] **Step 5: 运行** `pytest tests/test_mcp_server.py -q` → 全过。

---

## Task 5: 回归脚本 check 15

**Files:**
- Modify: `tools/test/feature-checks/run-checks.py`

- [ ] **Step 1: 新增 check**：`POST {base}/mcp`（`Accept: application/json, text/event-stream`）initialize → `result.serverInfo.name == "AutoFlow"`；`tools/list` 名称集合含 `run_flow/get_run/replay_run`；`tools/call list_capabilities` 的 `plugins` 非空。
- [ ] **Step 2: 本地回归**：临时容器（`-p 3001:3000 -v /tmp:/tmp`）跑 `run-checks.sh http://localhost:3001` → 74/74。

---

## Task 6: 文档与部署文件

**Files:**
- Create: `docs/zh/modules/mcp.md`
- Create: `flows/README.md`、`flows/example.flow.yaml`
- Modify: `docs/zh/modules/index.md`、`README.md`、`docs/roadmap.md`、`.env.example`、`docker-compose.yml`、`backend/Dockerfile`

- [ ] **Step 1: `flows/`**：示例 Flow 使用内置/dummy 动作，保证 `run_flow(flow_name="example")` 可复现；README 说明命名与放置规则。
- [ ] **Step 2: `docs/zh/modules/mcp.md`**：端点、工具表、token、异步轮询、Claude Code/Cursor 配置示例、curl 示例、安全提示。
- [ ] **Step 3: Dockerfile/compose/.env.example**：`COPY flows/ /app/flows/`；`./flows:/app/flows:ro`；三个环境变量注释。
- [ ] **Step 4: README/roadmap/模块索引**：核心能力加 MCP；roadmap 第 3 节 MCP 项标注"第一期已交付，反向 Agent-step 待做"。

---

## Task 7: 全量验证与交付

- [ ] **Step 1:** `cd backend && .venv/bin/python -m pytest -q`（预期 ≥165 passed）；`.venv/bin/ruff check . ../plugins` + `ruff format --check`。
- [ ] **Step 2:** 重建镜像并部署（`bash scripts/start.sh`），3101 healthy。
- [ ] **Step 3:** 手工 E2E：官方 `mcp` 客户端（`streamablehttp_client`）连接 `http://localhost:3101/mcp`：`list_capabilities` → `list_flows` → `run_flow(flow_name="example")` → `get_run` → `get_artifact`。
- [ ] **Step 4:** 容器回归 `run-checks.sh` ≥74/74；临时容器与 marker 清理。
- [ ] **Step 5:** pre-commit、提交、推送 `feat/mcp-bridge`、建 PR、等 CI 4/4 全绿。
