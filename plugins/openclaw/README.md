# OpenClaw Plugin

OpenClaw 插件为 AutoFlow 提供与 OpenClaw 生态系统集成的能力。

## 版本

0.1.0

## 功能概述

本插件提供以下 Action 和 Check：

### Actions

| 类型 | 描述 | 参数 |
|------|------|------|
| `openclaw.http_request` | 通用 HTTP 请求 | `method`, `url`, `headers`, `body`, `timeout` |
| `openclaw.exec` | 执行 Shell 命令 | `command`, `cwd`, `timeout` |
| `openclaw.knowflow_record` | 调用 KnowFlow 记录知识项 | `base_url`, `name`, `project_id`, `archive_type`, `summary`, `content`, `agent_source` |

### Checks

| 类型 | 描述 | 参数 |
|------|------|------|
| `openclaw.status_code_ok` | 检查 HTTP 状态码 | `expected` (默认 200) |
| `openclaw.exit_code_zero` | 检查命令退出码是否为 0 | 无 |

## 使用示例

### HTTP 请求

```json
{
  "type": "openclaw.http_request",
  "params": {
    "method": "GET",
    "url": "https://api.example.com/data",
    "timeout": 30
  }
}
```

响应：
```json
{
  "status_code": 200,
  "headers": { "Content-Type": "application/json" },
  "body": { "result": "success" }
}
```

### 执行 Shell 命令

```json
{
  "type": "openclaw.exec",
  "params": {
    "command": "echo Hello World",
    "timeout": 60
  }
}
```

响应：
```json
{
  "exit_code": 0,
  "stdout": "Hello World\n",
  "stderr": ""
}
```

### KnowFlow 记录

```json
{
  "type": "openclaw.knowflow_record",
  "params": {
    "base_url": "http://localhost:3000",
    "name": "测试文档",
    "project_id": "my-project",
    "archive_type": "document",
    "summary": "这是一个测试",
    "content": "详细内容...",
    "agent_source": "autoflow"
  }
}
```

响应：
```json
{
  "item_id": "abc123",
  "name": "测试文档",
  "success": true
}
```

### 状态码检查

```json
{
  "type": "openclaw.status_code_ok",
  "params": {
    "expected": 200
  }
}
```

### 退出码检查

```json
{
  "type": "openclaw.exit_code_zero",
  "params": {}
}
```

## 依赖

- Python 3.11+
- urllib (内置)
- json (内置)
- subprocess (内置)

无需额外安装依赖。