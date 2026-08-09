# Plugin SDK 规范（框架级）

本文档定义 AutoFlow 的插件扩展边界：插件如何声明能力、如何被加载、如何扩展 Trigger/Action/Check，以及如何进行最小权限的安全控制。

插件的业务说明与实现细节应放在各插件目录内（例如 `plugins/<plugin>/README.md`），不写进 `docs/`。

## 插件能力模型

插件可以扩展以下能力（可按需实现）：

- **TriggerType**：新增触发类型与配置 schema
- **ActionType**：新增动作类型与参数 schema
- **CheckType**：新增校验类型与参数 schema
- **UI 配置面板**：帮助用户生成 TriggerDoc/Flow（可选）

## 最小接口（抽象）

框架只依赖以下抽象概念：

- `PluginManifest`：插件元信息（名称、版本、能力声明、权限声明）
- `register(registry)`：向框架注册 Trigger/Action/Check 的实现与 schema

## Manifest（建议字段）

```yaml
name: zhihu-digest
version: 0.1.0
description: "知乎自动总结"
capabilities:
  triggers:
    - type: zhihu.question
  actions:
    - type: zhihu.fetchAnswers
    - type: ai.summarize
  checks:
    - type: text.contains
permissions:
  network:
    - "https://www.zhihu.com"
  secrets:
    - "zhihu.cookie"
    - "ai.apiKey"
```

约定：

- `version` 建议遵循语义化版本。
- `permissions` 仅用于声明意图，真正的能力控制由框架运行时实现。

## Schema 与校验

插件为每个扩展点提供 schema（例如 JSON Schema）：

- Trigger 配置 schema：用于校验 TriggerDoc 的 `trigger` 段
- Action/Check 参数 schema：用于校验 Flow 中的 `params`

框架应保证：

- schema 校验失败时，能定位到具体文件/字段/原因
- 未安装对应插件时，能提示缺失的 `type`

## 生命周期（建议）

- `load`：发现并加载插件包
- `init`：初始化（读取配置、建立连接池等）
- `register`：注册能力到运行时
- `dispose`：释放资源

## 安全边界（框架要求）

- **Secrets 不明文**：插件只能通过“Secrets 引用”访问凭证，严禁把凭证写入 Flow/TriggerDoc。
- **最小权限**：网络域名白名单、文件路径白名单等应可被运行时限制与审计。
- **产物脱敏**：日志与产物必须支持脱敏规则（由框架统一实现/插件可声明敏感字段）。
