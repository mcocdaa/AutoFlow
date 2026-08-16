---
title: Flow Plugin Runtime 参考示例
version: 1.0
keywords: [example, backend, frontend, plugin, adapter]
description: 插件端到端参考示例
---

# 端到端参考示例

本文件属于宿主集成资料。

本示例展示同一个 Python 插件如何先提供纯后端能力，再可选提供前端入口。代码用于固定接口语义，不是当前仓库中的实现。

## 1. 插件目录

```text
plugins/
├── plugins.yaml
└── meeting-export/
    ├── plugin.yaml
    └── meeting_export/
        ├── __init__.py
        └── plugin.py
```

部署注册表：

```yaml
plugins:
  meeting-export:
    path: meeting-export
    enabled: true
```

## 2. Manifest

```yaml
api_version: flow-plugin/v1
id: meeting-export
name: 会议导出
version: 1.0.0

runtime:
  language: python
  entrypoint: meeting_export.plugin:plugin
  python: ">=3.12,<3.14"

requires:
  - service: meetflow.exporters
    version: ">=2,<3"
  - service: flow.ui
    version: ">=1,<2"
    optional: true
  - service: flow.metrics
    version: ">=1,<2"
    optional: true

capabilities:
  exporters:
    - meeting-export.markdown
  ui_slots:
    - meeting.toolbar.action

config_schema:
  type: object
  additionalProperties: false
  properties:
    filename:
      type: string
      default: meeting.md

permissions:
  network: []
  filesystem: []
  secrets: []
```

## 3. 纯后端插件

```python
from flow_plugin_runtime.api import PluginRuntimeContext


def build_exporter(filename):
    async def export_markdown(invocation, payload):
        meeting = invocation.bounded_context
        content = render_markdown(meeting)
        return {
            "media_type": "text/markdown; charset=utf-8",
            "filename": filename,
            "content": content.encode("utf-8"),
        }

    return export_markdown


class MeetingExportPlugin:
    async def activate(self, ctx: PluginRuntimeContext, config):
        exporters = ctx.services.require("meetflow.exporters")
        exporters.register(
            "meeting-export.markdown",
            handler=build_exporter(config["filename"]),
            target_types=("meeting",),
            input_schema={
                "type": "object",
                "additionalProperties": False,
            },
        )


plugin = MeetingExportPlugin()
```

这里没有 `on_load()`、`on_unload()` 或 `stop()`。`exporters.register()` 已把注销函数放入当前 generation 的 EffectScope；配置值通过当前 generation 的闭包固定，不会被后续原地修改。

## 4. 后端运行过程

宿主启动时：

```python
runtime = Runtime(
    loader=DirectoryPluginLoader(plugins_dir),
    state_store=SqliteRuntimeStateStore(database),
)
await runtime.install(MeetFlowHostAdapter(app, database))
await runtime.discover()
await runtime.reconcile()
```

状态变化：

```text
meeting-export discovered
  → INACTIVE/MISSING_DEPENDENCY

MeetFlowHostAdapter provides meetflow.exporters@2
  → reconcile
  → meeting-export ACTIVATING generation=1
  → register exporter effect
  → ACTIVE generation=1
```

调用时：

```text
POST /api/plugin-runtime/v1/commands/meeting-export.markdown:invoke
  → current_user
  → require_meeting_view
  → build bounded meeting context
  → validate input
  → invoke export_markdown
  → validate output size/media type/filename
  → response
```

禁用时：

```text
desired_enabled=false
  → stop accepting new invocations
  → drain bounded in-flight invocations
  → DEACTIVATING
  → dispose exporter registration
  → INACTIVE/DISABLED
```

卸载后 Registry 中不再存在 `meeting-export.markdown`，但过去生成的文件、Job、Event 和会议数据不会被删除。

## 5. 增加声明式前端

同一个插件只需在 `activate()` 中检测可选 UI service：

```python
class MeetingExportPlugin:
    async def activate(self, ctx: PluginRuntimeContext, config):
        exporters = ctx.services.require("meetflow.exporters")
        exporters.register(
            "meeting-export.markdown",
            handler=build_exporter(config["filename"]),
            target_types=("meeting",),
            input_schema={
                "type": "object",
                "additionalProperties": False,
            },
        )

        ui = ctx.services.optional("flow.ui")
        if ui is not None:
            ui.register(
                id="meeting-export.toolbar-markdown",
                slot="meeting.toolbar.action",
                component="command-button",
                order=100,
                props={
                    "label": "导出 Markdown",
                    "command": "meeting-export.markdown",
                    "variant": "secondary",
                },
            )
```

UI 注册是第二个 effect。插件 effect 栈为：

```text
1. exporter:meeting-export.markdown
2. ui:meeting-export.toolbar-markdown
```

卸载时按逆序撤销 UI，再撤销 Exporter。

在本例中，MeetFlow Adapter 还会把 Exporter 投影为同 ID 的只读下载 Command，因此 UI Descriptor 可以引用 `meeting-export.markdown`；插件不需要重复注册第二个 handler。

## 6. Vue Host

MeetFlow 页面只保留固定插槽：

```vue
<PluginSlot
  slot="meeting.toolbar.action"
  target-type="meeting"
  :target-id="meeting.id"
/>
```

`PluginSlot` 请求 Descriptor：

```text
GET /api/plugin-runtime/v1/ui/meeting.toolbar.action
    ?target_type=meeting
    &target_id=m-123
```

Host Bridge 把 `command-button` 映射为 MeetFlow 自己的按钮。按钮点击后调用后端 Command，不执行插件 JavaScript。

## 7. React Host

如果相同协议由 KnowFlow 使用，页面写法可以是：

```tsx
<PluginSlot
  slot="item.detail.action"
  targetType="item"
  targetId={item.id}
/>
```

React Bridge 消费相同 Descriptor schema，但渲染 KnowFlow 自己的组件和样式。

## 8. 依赖动态变化

若 `meetflow.exporters` 被替换：

```text
provider generation 4 disappears
  → meeting-export generation 1 stops accepting invocation
  → dispose UI and Exporter
  → INACTIVE/MISSING_DEPENDENCY

provider generation 5 becomes READY
  → activate meeting-export generation 2
  → contributions bind to provider generation 5
  → ACTIVE
```

插件本身没有监听依赖事件，也没有维护 `started` 布尔值。

## 9. 激活失败

如果 Exporter 注册成功后 UI 注册校验失败：

```text
Exporter effect acquired
  → UI effect raises capability validation error
  → staging scope reverse rollback
  → Exporter registration removed
  → plugin FAILED/ACTIVATION_FAILED
```

外部调用者从未看到半激活插件。

## 10. 可选 Child Component

假设指标能力不是导出功能的启动前提，可以声明独立 child：

```python
from flow_plugin_runtime.api import ComponentSpec, ServiceRequirement


async def activate_metrics(ctx, config):
    metrics = ctx.services.require("flow.metrics")
    await ctx.effects.acquire(
        "metrics:meeting-export.usage",
        lambda: metrics.open_counter(
            "meeting-export.usage",
            labels={"format": "markdown"},
        ),
    )


metrics_component = ComponentSpec(
    local_id="metrics",
    requires=(
        ServiceRequirement(service="flow.metrics", version=">=1,<2"),
    ),
    activate=activate_metrics,
)


class MeetingExportPlugin:
    async def activate(self, ctx, config):
        exporters = ctx.services.require("meetflow.exporters")
        exporters.register(
            "meeting-export.markdown",
            handler=build_exporter(config["filename"]),
            target_types=("meeting",),
            input_schema={
                "type": "object",
                "additionalProperties": False,
            },
        )
        ctx.components.mount(metrics_component)
```

Manifest 已把 `flow.metrics` 声明为 package 级 optional 上限。运行时行为是：

```text
meeting-export root ACTIVE
  └── metrics child INACTIVE/MISSING_DEPENDENCY

flow.metrics provider appears
  → only metrics child activates
  → meeting-export root does not reload

meeting-export root deactivates
  → metrics child deactivates first
  → root effects dispose afterward
```

如果需要为多个 workspace 提供互不干扰的同名服务，父组件先通过 `ctx.context.isolate(service_id)` 创建分支，再把该分支的后代 Context 传给 `mount()`。隔离只改变服务 resolution key，不增加 Manifest 权限。

## 11. 热替换失败恢复

开发环境显式选择 `ROLLBACK` 后，新代码激活失败的结果是：

```text
prepare candidate code_epoch=9 while generation=21 remains ACTIVE
  → deactivate old component tree
  → candidate generation=22 staging activation fails
  → rollback every candidate effect
  → restore checkpoint code_epoch=8
  → activate old code as generation=23
  → reload operation ROLLED_BACK
```

Generation 21 不会复活；恢复的是相同旧代码的新 generation 23。如果 candidate cleanup 或旧代码重新激活失败，插件保持 FAILED，Runtime 不会让新旧代码同时运行。
