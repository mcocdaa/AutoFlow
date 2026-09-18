schema: spec-driven
created: 2026-09-18

# MCP / Agent 双向桥(2026-09-18)

## 背景

AutoFlow 定位为"Agent 的确定性执行层":Agent 能调度动作,但缺少审计、重试、产物与回放。当前只有 REST API,Agent 生态(Cursor、Claude Code/Desktop 等)通用协议为 MCP,缺少标准接入点。

## 变更摘要(第一期:MCP Server)

1. **MCP 端点**:单镜像内 `/mcp`(Streamable HTTP,stateless + JSON 响应),SDK `mcp>=2.2.0`;4 worker 下无会话粘性问题。
2. **工具集(Flow 级 + 只读)**:`list_capabilities`、`list_flows`、`run_flow`、`get_run`、`list_runs`、`replay_run`、`get_artifact`。
3. **Flow 来源**:根目录 `flows/`(发现式,支持 stem/name 匹配) + `run_flow` 内联 YAML(AI 起草);统一落 `request.json` 供回放。
4. **执行模式**:默认同步(线程池,不阻塞事件循环);`wait=false` 后台线程执行,`get_run` 轮询(每步落盘)。
5. **鉴权**:可选 `MCP_TOKEN` Bearer(自实现 ASGI 中间件,constant-time);未设置时与现有 API 同等并文档化警示。
6. **部署与文档**:Dockerfile/compose 挂载 `flows/`;`.env.example` 新增 `MCP_ENABLED`/`MCP_TOKEN`/`FLOWS_DIR`;新增 `docs/zh/modules/mcp.md` 与回归 check 15。

## 约束遵循

- REST API 完全向后兼容,不新增端口;
- 不引入反向 Agent-step(下期)、不做 Action 级工具、不做 MCP resources/prompts;
- 路径安全:`flows/` 名称限定目录内;`get_artifact` 防穿越、256 KiB 截断;
- 执行面与现有 `/runs/execute` 等价,不扩大权限。

## 详细设计

见 `docs/superpowers/specs/2026-09-18-mcp-bridge-design.md`;
实施计划见 `docs/superpowers/plans/2026-09-18-mcp-bridge.md`。
