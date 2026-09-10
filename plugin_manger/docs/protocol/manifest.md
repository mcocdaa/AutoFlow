---
title: Flow Plugin Manifest 规范
version: 1.0
keywords: [manifest, schema, requires, provides, permission]
description: 插件静态声明与兼容规范
---

# Manifest 规范

本文件属于 `flow-plugin/v1` 核心协议。

## 1. 示例

```yaml
api_version: flow-plugin/v1
id: meeting-export
name: 会议导出
version: 1.2.0
description: 将有界会议上下文导出为 Markdown

runtime:
  language: python
  entrypoint: meeting_export.plugin:plugin
  python: ">=3.12,<3.14"

requires:
  - service: flow.logging
    version: ">=1,<2"
  - service: meetflow.exporters
    version: ">=2,<3"
  - service: flow.ui
    version: ">=1,<2"
    optional: true

provides: []

capabilities:
  exporters:
    - meeting-export.markdown
  ui_slots:
    - meeting.toolbar.action

config_schema:
  type: object
  additionalProperties: false
  properties:
    include_raw_notes:
      type: boolean
      default: false

permissions:
  network: []
  filesystem: []
  secrets: []

compatibility:
  hosts:
    meetflow: ">=1.0,<2.0"
```

## 2. 顶层字段

| 字段 | 必须 | 说明 |
| --- | --- | --- |
| `api_version` | 是 | 固定为 `flow-plugin/v1` |
| `id` | 是 | 全局插件 ID |
| `name` | 是 | 面向管理员的名称 |
| `version` | 是 | 插件 SemVer 版本 |
| `description` | 否 | 不超过 240 字符的说明 |
| `runtime` | 是 | 语言、入口和 Python 兼容范围 |
| `requires` | 否 | 激活所需的动态服务 |
| `provides` | 否 | 激活后可能提供的命名服务 |
| `capabilities` | 否 | 对宿主扩展点的静态贡献声明 |
| `config_schema` | 否 | JSON Schema 2020-12 子集 |
| `permissions` | 是 | 网络、文件与密钥声明 |
| `compatibility` | 否 | 宿主和 Adapter 版本范围 |

未知顶层字段必须被拒绝，不能静默忽略。

## 3. 命名规则

### 3.1 插件 ID

`id` 必须匹配：

```regex
^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$
```

ID 一旦发布不得修改。显示名、代码目录和 Python 模块名可以变化。

### 3.2 Service ID

Service ID 必须匹配：

```regex
^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$
```

通用服务使用 `flow.*`；项目服务使用项目命名空间，如 `autoflow.actions`。

### 3.3 Contribution ID

插件自有 contribution 必须以 `<plugin-id>.` 开头。Host 固定 slot 等公共 ID 不受此前缀限制。

## 4. Runtime

第一版只允许：

```yaml
runtime:
  language: python
  entrypoint: package.module:object
  python: ">=3.12,<3.14"
```

`entrypoint` 必须是模块路径和导出对象，不允许文件系统绝对路径、`..`、URL 或命令行。Loader 只在经过验证的插件安装根目录中解析模块。

入口对象必须是 `PluginEntrypoint` 或等价 callable。模块导入阶段必须无副作用。

## 5. Requires

每个依赖项结构如下：

```yaml
- service: meetflow.exporters
  version: ">=2,<3"
  optional: false
```

字段语义：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `service` | 无 | 所需服务 ID |
| `version` | `*` | provider service 版本范围 |
| `optional` | `false` | 缺失时是否允许激活 |

Root component 的必需依赖采用 AND 语义，每个 `(service_id, resolution_key)` 必须恰好绑定一个 ACTIVE provider；零个表示缺失。若 desired graph 中存在多个兼容 provider candidates，Runtime 必须在执行 provider activation 前把全部冲突 candidates 标记为 `INACTIVE/AMBIGUOUS_PROVIDER`，其 consumers 同样保持 `INACTIVE/AMBIGUOUS_PROVIDER`。Runtime 不使用隐式 priority、注册顺序或版本最高规则来选择 provider；第二个 provider 提交仍必须作为防御性校验被拒绝并回滚当前 activation。

provider 的 ACTIVE generation 一旦撤销、替换或健康状态变为不可用，所有声明为必需依赖的 consumer 都必须自动 deactivation；新的 provider generation 可用后再自动 activation。这个行为不提供关闭必需依赖 reload 的字段。`optional: true` 只表示 package 可以通过 `get()` 观察该 service，不建立阻塞 component 激活的依赖边；需要随 provider 动态激活/撤销的功能必须建模为 child component 的必需 `requires`。

`flow-plugin/v1` 不支持多 provider service。需要多实现集合时，Host 应提供唯一的聚合 service，再由该 service 暴露有类型的 registrar/list API；Action、Exporter 和 Hook 集合本身属于这种 capability registrar，而不是多个同名 service provider。

Manifest `requires` 同时是整个 Plugin package 的服务访问上限。仅供 child component 使用的服务必须在 Manifest 中声明为 `optional: true`；child 可以在自己的 `ComponentSpec.requires` 中把它收紧为必需依赖，但不能增加未声明服务或放宽 version range。完整规则见 [components.md](components.md)。

第一版不支持任意布尔表达式、动态代码条件或基于配置拼接 Service ID。

### 5.1 可选 service 访问

可选 service 不会阻止 component 激活，也不会因为 provider 出现或消失自动重载当前 component。插件必须通过 SDK 的明确读取 API 访问它们：

```python
ctx.services.require("flow.logging")  # 缺失或非 ACTIVE 时抛出受控错误
ctx.services.get("flow.ui")  # 缺失时返回 None
```

`get()` 只返回调用时的当前 ACTIVE provider snapshot，不能被 activation effect、registrar、长期 handler 或进程级变量捕获；它只适合即时只读查询。Runtime/diagnostics 若需要观察撤销中的 provider，必须显式使用内部的非严格读取，不得把该结果当成已满足的依赖。需要 provider 出现/消失时自动重建资源时，插件必须把该服务放进 child `ComponentSpec.requires`，而不是在 root 中手工轮询。规范不提供未定义的 `ctx.services.optional()` 方法。

依赖对象的未知字段也必须拒绝。`reload_on_change` 和 `many` 都不是 `flow-plugin/v1` 字段；旧 Manifest 含有这些字段时必须报告 `manifest_invalid`，不能静默忽略或改变依赖语义。

## 6. Provides

插件提供服务时必须声明：

```yaml
provides:
  - service: ai.summarizer
    version: 1.1.0
    owner: root
```

`owner` 只允许：

| 值 | 默认 | 说明 |
| --- | --- | --- |
| `root` | 是 | 由 Plugin root component 声明为 provider candidate |
| `child` | 否 | 作为 child components 的 package 权限上限，具体 owner 由 `ComponentSpec.provides` 声明 |

声明只建立 provider candidate 或 package 上限，不使服务立即可用。只有对应 component 成功激活并提交 `ctx.services.provide()` effect 后，服务才进入其 ScopedContext 对应的 resolution key。一个 `(service_id, resolution_key)` 默认只能有一个 ACTIVE provider；重复提交必须失败并回滚当前 activation。

实际提供的 Service ID、版本和 owner 类型必须与 Manifest 匹配。Root 不能提供 `owner: child` 的服务，child 不能提供 `owner: root` 的服务。声明但未提供允许存在；提供但未声明或 owner 不匹配必须导致当前 component 激活失败并回滚。

第一版禁止 `owner: any`。同一服务确实需要 root 和 child 都能提供时，必须使用两个不同的 Service ID，避免依赖图把 package 权限误判为具体 provider。

## 7. Capabilities

`capabilities` 是由 Host Adapter 注册并校验的有类型 mapping。FPR Core 只负责保留和分发，不解释项目字段。

所有宿主必须支持以下通用 key：

```yaml
capabilities:
  commands: []
  event_subscriptions: []
  ui_slots: []
```

项目可以增加 namespaced key：

```yaml
capabilities:
  autoflow.actions:
    - zhihu.fetch-answer
  autoflow.checks:
    - zhihu.answer-exists
```

Adapter 必须做到：

1. 校验 capability key 已知；
2. 校验 contribution ID、schema 和数量限制；
3. 拒绝实际注册但未声明的 contribution；
4. 在卸载时撤销所有 contribution。

## 8. Config Schema

`config_schema` 使用 JSON Schema 2020-12 的可移植子集：

- `type`、`properties`、`required`；
- `additionalProperties`；
- `enum`、`const`；
- string/number/integer/array/object 的长度与范围；
- `default`、`title`、`description`。

禁止使用远程 `$ref`、动态 schema 代码或宿主不支持的自定义 validator。

配置处理顺序固定为：

```text
持久化原始配置
  → JSON Schema 校验与默认值归一化
  → 生成不可变 config snapshot
  → activation generation 使用该 snapshot
```

配置更新不能原地修改 ACTIVE 插件对象，必须触发新 generation 的 deactivate → activate。

## 9. Secrets

Manifest 只声明插件允许读取的 secret key：

```yaml
permissions:
  secrets:
    - llm_api_key
```

配置中保存的是 secret reference 或宿主加密后的值，禁止在 Manifest、普通配置、日志、诊断和 UI Descriptor 中出现明文。

插件通过 `ctx.secrets.get("llm_api_key")` 获取当前 generation 的值。未声明的 key 必须拒绝访问。

## 10. Permissions

```yaml
permissions:
  network:
    - https://api.example.com
  filesystem:
    - scope: artifacts
      access: write
  secrets:
    - llm_api_key
```

权限声明是 Adapter 的强制 allowlist 输入，不是 Python 沙箱。插件仍是受信任代码；绕过 Adapter 直接调用 Python 标准库无法被进程内 Runtime 彻底阻止。

需要强隔离的插件必须交给未来的 subprocess/container Execution Adapter，不能把 Manifest 权限宣称为安全隔离。

## 11. Compatibility

```yaml
compatibility:
  hosts:
    autoflow: ">=2.0,<3.0"
  adapters:
    flow.fastapi: ">=1,<2"
```

Host 和 Adapter 版本不满足时，插件保持 `INACTIVE`，reason 为 `INCOMPATIBLE_HOST` 或 `INCOMPATIBLE_ADAPTER`，不得尝试导入入口模块。

## 12. Registry 与持久化覆盖

安装清单描述插件本身；部署注册表描述是否安装和默认启用：

```yaml
plugins:
  meeting-export:
    path: meeting-export
    enabled: true
```

运行时持久化状态可以覆盖 `enabled` 和 config，但不能覆盖插件 ID、版本、入口、依赖或权限声明。

解析优先级固定为：

```text
Manifest 静态定义
  + Deployment Registry 默认值
  + RuntimeStateStore 管理员覆盖
```

状态来源必须在诊断中显示，避免管理员误以为修改 YAML 已立即改变全部进程。
