---
title: Flow 目录
description: MCP Agent 可发现的 Flow 放置约定
keywords: [flows, MCP, Agent, 目录]
version: "1.0"
---

# Flow 目录

本目录用于放置希望被 Agent 通过 MCP 发现的 Flow。`list_flows` 会扫描这里，`run_flow(flow_name=...)` 按以下顺序匹配：

1. 文件 stem（如 `example.flow.yaml` → `example.flow`）
2. 去掉 `.flow` 后缀的 stem（如 `example`）
3. YAML 顶层的 `name` 字段

## 约定

- 文件名使用 `*.flow.yaml`（非递归，`*.yaml`/`*.yml` 也接受）
- 顶层结构遵循 [Flow 规范](../docs/zh/specs/flow.md)：`version` / `name` / `steps`
- 无法解析的文件不会中断扫描，会在 `list_flows` 的 `errors` 中列出原因

## 运行方式

```bash
# 查看可用流程
curl -s http://localhost:3001/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"list_flows","arguments":{}}}'

# 执行示例流程
# tools/call run_flow {"flow_name": "example", "wait": true}
```

Docker 部署时本目录挂载为容器内 `/app/flows`（只读），也可用环境变量 `FLOWS_DIR` 指向其他位置。更多说明见 [MCP 模块文档](../docs/zh/modules/mcp.md)。
