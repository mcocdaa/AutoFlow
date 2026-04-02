# Flow 规范

本文档定义 AutoFlow 的 Flow（流程）数据结构与最小运行语义，用于在不同端（桌面/移动/后端）之间保持一致的“可执行契约”。

## 设计目标

- **可版本化**：Flow 文件可作为资产存储与回滚
- **可扩展**：Action/Check 可由插件扩展，不修改核心解析器
- **可观测**：每个 Step 有稳定的标识，便于日志/产物关联

## 基本结构（YAML）

```yaml
version: 1
name: desktop-checkin
description: "桌面自动打卡流程"

defaults:
  timeoutMs: 30000
  retry:
    maxAttempts: 1
    backoffMs: 0

steps:
  - id: open-app
    name: "打开应用"
    action:
      type: desktop.launch
      params:
        app: "/Applications/Foo.app"
    check:
      type: desktop.windowTitleContains
      params:
        text: "Foo"

  - id: click-checkin
    action:
      type: desktop.click
      params:
        by: ocr
        text: "打卡"
```

## 字段定义

### 顶层

- `version`：整数，Flow 版本号（必填）
- `name`：流程名（必填）
- `description`：说明（可选）
- `defaults`：默认执行策略（可选）
- `steps`：Step 数组（必填，至少 1 个）

### defaults

- `timeoutMs`：单步默认超时（毫秒）
- `retry.maxAttempts`：默认最大尝试次数（包含首次）
- `retry.backoffMs`：固定退避时间（毫秒）；复杂策略由 Runner 统一扩展

### Step

- `id`：稳定标识（必填，建议短横线命名；同一 Flow 内唯一）
- `name`：展示名（可选）
- `action`：动作定义（必填）
- `check`：结果校验（可选；不填则默认不校验）
- `timeoutMs`：覆盖默认超时（可选）
- `retry`：覆盖默认重试策略（可选）

## Action

Action 是“做什么”。其结构由框架约定、由插件扩展。

通用字段：

- `type`：动作类型（必填，例如 `http.request`、`desktop.click`）
- `params`：动作参数（可选，结构由 `type` 决定）

约定：

- Action 不应直接访问明文密钥；如需凭证，使用 Secrets 引用（见 `docs/zh/modules/secrets.md`）。
- Action 需要输出结构化结果，供 Check 使用（由 Runner 规范化）。

## Check

Check 是“怎么确认”。其结构也由插件扩展。

通用字段：

- `type`：校验类型（必填，例如 `text.contains`、`desktop.elementExists`）
- `params`：校验参数（可选）

约定：

- 未配置 Check 时，Runner 将此 Step 视为“无校验模式”，只记录 Action 结果与产物。

## 兼容与演进

- `version` 递增时，保证旧版本可读（至少在一个大版本周期内）。
- 新增字段应保持默认值可推导，避免破坏旧 Flow。
- `type` 扩展由插件注册，解析器只做结构校验与分发，不硬编码业务。
