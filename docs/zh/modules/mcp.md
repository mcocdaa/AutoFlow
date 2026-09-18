---
title: MCP 模块
description: 把 Flow 以 MCP 工具暴露给 Agent
keywords: [MCP, Agent, 工具, 集成]
version: "1.0"
---

# MCP 模块

AutoFlow 在同一个镜像内提供 **MCP（Model Context Protocol）Server**，把 Flow 能力以工具暴露给任意支持 MCP 的 Agent（Claude Code/Desktop、Cursor 等）。Agent 调用得到的是"有历史、有产物、可回放"的运行，而不是裸命令。

- 端点：`POST /mcp`（Streamable HTTP，stateless + JSON 响应），与前端/API 同端口
- 开关：环境变量 `MCP_ENABLED`（默认开启）
- 鉴权：环境变量 `MCP_TOKEN` 非空时要求 `Authorization: Bearer <token>`

## 工具清单

| 工具 | 入参 | 说明 |
|---|---|---|
| `list_capabilities` | — | 已加载插件、已注册 Action/Check 与插件错误 |
| `list_flows` | — | `flows/` 目录内可用 Flow 与无法解析的文件 |
| `run_flow` | `flow_name` 或 `flow_yaml`、`input`、`vars`、`wait` | 执行 Flow；`wait=true` 阻塞返回结果，`false` 返回 `run_id` |
| `get_run` | `run_id` | 查询运行（运行中可见已完成步骤） |
| `list_runs` | `limit` | 最近运行（默认 20） |
| `replay_run` | `run_id`、`wait` | 重放保存的请求，生成新运行 |
| `get_artifact` | `run_id`、`path`、`max_bytes` | 读取文本产物（默认上限 256 KiB，超出截断） |

`flows/` 目录约定见仓库根 [flows/README.md](../../flows/README.md)；也可用 `FLOWS_DIR` 指向其他目录。

## 客户端配置

Claude Code（`.mcp.json` 或项目配置）：

```json
{
  "mcpServers": {
    "autoflow": {
      "type": "http",
      "url": "http://localhost:3001/mcp",
      "headers": { "Authorization": "Bearer <MCP_TOKEN>" }
    }
  }
}
```

Cursor：把 `type` 换成 `"url"` 字段即可（`"url": "http://localhost:3001/mcp"`）。未设置 `MCP_TOKEN` 时省略 `headers`。

## 使用示例（curl）

```bash
# 初始化握手
curl -s http://localhost:3001/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2025-06-18","capabilities":{},
                 "clientInfo":{"name":"curl","version":"0"}}}'

# 调用 run_flow（同步）
curl -s http://localhost:3001/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"run_flow",
                 "arguments":{"flow_name":"example","wait":true}}}'

# 异步：wait=false 后轮询 get_run
# arguments: {"name":"get_run","arguments":{"run_id":"<id>"}}
```

## 执行模式与限制

- `wait=false` 每次调用启动一个后台线程，无队列与并发上限；进程重启后遗留的 `running` 运行需人工处理（后续 Trigger 运行时统一治理）
- 大输出与产物仍按 `__artifact__` 索引，用 `get_artifact` 读取
- `/mcp` 与 REST API 权限等价（可执行 `openclaw.exec` 等插件动作）：未设置 `MCP_TOKEN` 时请勿暴露到公网，生产部署置于内网或网关之后
