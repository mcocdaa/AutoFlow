# TriggerDoc 规范

TriggerDoc（触发文档）用于描述“为什么/何时跑”：它把触发器（Trigger）与要执行的 Flow 关联起来，并允许声明运行策略（例如是否启用校验）。

TriggerDoc 的目标是：任务可以像代码一样被管理（版本化、审计、复用），并能由 UI 辅助生成。

## 基本结构（YAML）

```yaml
version: 1
name: zhihu-digest

trigger:
  type: zhihu.question
  mode: link # link | cron-random
  link: https://www.zhihu.com/question/xxxx
  cron: "0 9 * * *" # mode=cron-random 时生效

flow:
  ref: flows/zhihu-digest.flow.yaml
  params:
    aiProvider: "openai"
    model: "gpt-4.1"

policy:
  checksEnabled: true
  concurrencyKey: "zhihu-digest"
```

## 字段定义

### 顶层

- `version`：整数，TriggerDoc 版本号（必填）
- `name`：任务名（必填）
- `trigger`：触发器定义（必填）
- `flow`：关联的 Flow（必填）
- `policy`：运行策略（可选）

### trigger

- `type`：触发类型（必填，由框架或插件提供，例如 `cron`、`webhook`、`zhihu.question`）
- `mode`：同一 type 下的子模式（可选，由插件定义）
- 其它字段：由 `type`/`mode` 决定（例如 `cron` 表达式、URL、文件路径等）

约定：

- `trigger.type` 的枚举由插件扩展，但必须提供对应的配置 schema 与校验规则（见 Plugin SDK）。
- Trigger 触发后应产出结构化的 `triggerContext` 传递给 Runner（例如链接、随机选择结果、事件 payload）。

### flow

- `ref`：Flow 文件引用（必填，相对路径或资源标识）
- `params`：运行参数（可选，注入到 Flow/Action 的上下文中）

### policy

- `checksEnabled`：是否启用 Step 级 Check（默认 `false` 或由 Runner 默认值决定）
- `concurrencyKey`：并发约束键（可选，用于防止同类任务并发冲突）

## 兼容与演进

- `version` 递增时保持旧版本可读；新增字段必须可选且有合理默认值。
- 插件扩展的 Trigger 必须保证“未知字段可忽略、未知 type 可报错可提示”的可诊断性。
