---
title: MCP Module
description: Exposing Flows as MCP tools to AI Agents
keywords: [MCP, Agent, tools, integration]
version: "1.0"
---

# MCP Module

AutoFlow provides a built-in **MCP (Model Context Protocol) Server** inside the same container image, exposing workflow capabilities as structured tools to any MCP-compatible AI Agent (Claude Code/Desktop, Cursor, OpenClaw, etc.). Instead of raw shell commands, agent invocations produce auditable, replayable runs with persisted history and artifacts.

- Endpoint: `POST /mcp` (Streamable HTTP, stateless + JSON response), served on the same port as the WebUI and REST API
- Toggle: environment variable `MCP_ENABLED` (enabled by default)
- Authentication: when `MCP_TOKEN` is non-empty, requires `Authorization: Bearer <token>`

## Available Tools

| Tool | Arguments | Description |
|---|---|---|
| `list_capabilities` | — | List loaded plugins, registered Actions/Checks, and plugin load errors |
| `list_flows` | — | List available Flows under `flows/` and any unparseable files |
| `run_flow` | `flow_name` or `flow_yaml`, `input`, `vars`, `wait` | Execute a Flow; `wait=true` blocks until completion, `false` returns `run_id` immediately |
| `get_run` | `run_id` | Query a run (completed steps are visible while running) |
| `list_runs` | `limit` | List recent runs (default 20) |
| `replay_run` | `run_id`, `wait` | Replay a stored run request to create a new run |
| `get_artifact` | `run_id`, `path`, `max_bytes` | Read a text artifact (default limit 256 KiB, truncated if exceeded) |

See [flows/README.md](../../../flows/README.md) at the repository root for `flows/` directory conventions; you can also point `FLOWS_DIR` to another directory.

## Client Configuration

Claude Code (`.mcp.json` or project settings):

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

Cursor: replace `type` with the `"url"` field (`"url": "http://localhost:3001/mcp"`). Omit `headers` when `MCP_TOKEN` is not set.

## Usage Example (curl)

```bash
# Initialize handshake
curl -s http://localhost:3001/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2025-06-18","capabilities":{},
                 "clientInfo":{"name":"curl","version":"0"}}}'

# Invoke run_flow (synchronous)
curl -s http://localhost:3001/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"run_flow",
                 "arguments":{"flow_name":"example","wait":true}}}'

# Asynchronous: poll get_run after wait=false
# arguments: {"name":"get_run","arguments":{"run_id":"<id>"}}
```

## Execution Mode & Limitations

- `wait=false` spawns a background thread per call without queuing or concurrency limits; stale `running` records after a process restart must be cleaned up manually or by the storage GC
- Large outputs and files are indexed via `__artifact__` and read with `get_artifact`
- `/mcp` has the same privileges as the REST API (can execute plugin actions such as `openclaw.exec`): do not expose an unauthenticated instance (`MCP_TOKEN` unset) to the public internet; deploy behind an internal network or authenticated gateway
