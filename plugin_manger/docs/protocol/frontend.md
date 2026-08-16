---
title: Flow Plugin 声明式前端规范
version: 1.0
keywords: [frontend, ui, descriptor, vue, react]
description: Python插件前端桥接协议
---

# 声明式前端协议

本文件属于 `flow-plugin/v1` 核心协议。

## 1. 原则

第一版插件只写 Python。插件通过 `flow.ui` 注册 UI Descriptor；后端 Runtime 拥有它的生命周期；Vue/React 只渲染后端返回的已授权描述。

```text
Python plugin activate
  → ctx.ui.register(descriptor)
  → Runtime effect catalog
  → GET /ui/{slot}
  → Vue/React PluginSlot
  → Host 原生组件
```

前端没有插件发现、依赖图、配置或启停状态机。

## 2. Descriptor

```json
{
  "id": "meeting-export.toolbar-markdown",
  "plugin_id": "meeting-export",
  "slot": "meeting.toolbar.action",
  "component": "command-button",
  "order": 100,
  "props": {
    "label": "导出 Markdown",
    "command": "meeting-export.markdown",
    "variant": "secondary"
  }
}
```

必须字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 插件内稳定、全局唯一的 contribution ID |
| `plugin_id` | 由 Runtime 注入，不接受插件伪造 |
| `slot` | Host 注册的固定插槽 |
| `component` | Host 支持的受控组件类型 |
| `order` | 排序值，默认 100 |
| `props` | 经过 component schema 校验的 JSON |

响应按 `order`、`plugin_id`、`id` 稳定排序。

## 3. 第一版组件

通用 Host Bridge 应支持：

| component | 用途 |
| --- | --- |
| `command-button` | 调用后端 Command |
| `command-menu-item` | 在固定菜单中调用 Command |
| `schema-form` | 按 JSON Schema 收集输入并调用 Command |
| `info-card` | 展示安全的键值、状态和链接 |
| `badge` | 展示短状态 |
| `markdown-panel` | 展示后端返回的受限 Markdown |

项目可以增加 namespaced component，例如 `knowflow.attribute-field`，但必须在 Host Bridge 中静态注册 schema 和渲染器。

Descriptor 禁止包含：

- HTML、JavaScript、CSS 源码；
- Vue/React 组件路径；
- 动态 import URL；
- 事件处理函数文本；
- secret、access token 或后端内部路径；
- 未经 Host allowlist 的外部 URL。

## 4. Slot

Slot 由 Host 注册：

```python
UiSlotDefinition(
    id="meeting.toolbar.action",
    target_types=("meeting",),
    allowed_components=("command-button", "command-menu-item"),
    max_items=8,
)
```

插件只能使用 Manifest `capabilities.ui_slots` 声明过的 slot。Host 可以基于 actor、target、产品版本或 feature flag 过滤，但不能改变 Descriptor 的插件归属。

## 5. UI 查询

```text
GET /api/plugin-runtime/v1/ui/meeting.toolbar.action
    ?target_type=meeting
    &target_id=<id>
```

后端必须先完成：

1. 用户认证；
2. target 存在性和访问授权；
3. slot 与 target type 校验；
4. 插件 ACTIVE generation 校验；
5. Descriptor schema 校验；
6. 按权限和条件过滤。

响应不包含插件配置和依赖诊断。

## 6. Command 调用

`command-button` 不携带任意 URL，只携带 command ID：

```json
{
  "target_type": "meeting",
  "target_id": "m-123",
  "input": {},
  "invocation_id": "client-generated-uuid"
}
```

前端调用稳定 dispatcher：

```text
POST /api/plugin-runtime/v1/commands/meeting-export.markdown:invoke
```

后端重新鉴权、加载 bounded context 并校验 input。Descriptor 不是授权凭证。

## 7. Vue/React Host Bridge

Vue 与 React 分别实现一个项目内桥接组件：

```text
PluginSlot
  ├─ usePluginDescriptors(slot, target)
  ├─ component registry
  ├─ per-item error boundary
  ├─ loading/empty/error policy
  └─ command client
```

Bridge 可以复用一个语言中立 JSON Schema 测试集，但第一版不要求发布 TypeScript SDK。

同一 Descriptor 在不同产品中可以有不同视觉样式；行为、command 和 props 语义必须一致。

## 8. 错误隔离

- UI 查询失败不得让核心页面失败；
- 单个 Descriptor 无效时只忽略该项并记录诊断；
- 单个渲染器异常由 item error boundary 隔离；
- Command 失败显示 Host 统一错误，不渲染插件返回的任意 HTML；
- 插件在请求过程中被卸载时，后端返回稳定的 `plugin_inactive` 冲突响应。

## 9. 缓存与刷新

UI 响应必须包含 `runtime_epoch`。Host Bridge 可以按 `(slot, target, actor, runtime_epoch)` 缓存。

插件启停或 generation 变化后，Runtime 发布 epoch；前端可通过页面刷新、轮询或宿主已有事件通道重新查询。第一版不要求 FPR 自带 WebSocket。

## 10. 可访问性与国际化

Descriptor 中的 label 是默认文案。Host 可以使用 `label_key` 映射已有 locale，但不得执行插件提供的翻译代码。

渲染器必须遵守宿主的键盘、焦点、ARIA、颜色和错误提示规范。插件只描述意图，不能覆盖这些要求。

## 11. 复杂前端扩展

任意 JavaScript `frontend_entry` 不属于 `flow-plugin/v1`。未来若确有需求，必须定义独立协议版本，并至少满足：

- 只能注册固定 slot；
- 每次注册返回 disposer；
- 模块和 Host API 有版本协商；
- CSP、来源、完整性和错误隔离明确；
- 不能访问后端 secret；
- Python Runtime 仍是启停和授权的权威来源。

在该协议正式定义前，四个项目不应继续扩展各自的任意前端模块 ABI。
