# AutoFlow Skill

桥接 AutoFlow 流程自动化引擎，让 OpenClaw Agent 能够执行和管理自动化工作流。

## 概述

AutoFlow 是一个工作流自动化引擎，支持通过 YAML 定义流程，并执行各种动作（Actions）和检查（Checks）。此插件提供 3 个工具与 AutoFlow 进行交互。

## 工具

### 1. autoflow_run

执行一个 AutoFlow 工作流。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| flowYaml | string | ✅ | Flow YAML 定义内容 |
| input | object | ❌ | 传递给 Flow 的输入数据 |
| vars | object | ❌ | 注入 Flow 上下文的变量 |

**返回值：** 执行结果 JSON，包含 run_id、status、output 等字段。

**示例：**
```json
{
  "flowYaml": "name: hello\nsteps:\n  - name: greet\n    action: echo\n    input:\n      message: \"Hello, World!\"",
  "input": { "name": "John" },
  "vars": { "debug": true }
}
```

### 2. autoflow_list

列出所有工作流执行记录。

**参数：** 无

**返回值：** 运行记录列表，包含每个 run 的 id、status、start_time、end_time 等信息。

**示例：**
```json
{}
```

### 3. autoflow_plugins

查询 AutoFlow 系统注册的插件、可用动作和检查项。

**参数：** 无

**返回值：** 
- `plugins`: 已注册的插件列表（name, version）
- `actions`: 可用的动作类型列表
- `checks`: 可用的检查类型列表

**示例：**
```json
{}
```

## 配置

插件支持通过 `baseUrl` 配置项指定 AutoFlow API 地址：

```json
{
  "baseUrl": "http://localhost:8000"
}
```

默认值为 `http://localhost:8000`。