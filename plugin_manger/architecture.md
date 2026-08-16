---
title: Flow Plugin Runtime 总体架构
version: 1.0
keywords: [architecture, context, host, adapter, plugin]
description: 通用插件运行时总体架构
---

# 总体架构

## 1. 设计目标

FPR 解决四类重复问题：

1. 每个项目各自扫描 YAML、导入 Python 模块和维护插件清单；
2. 插件注册 Action、Hook、Route、Key 或 UI 后，卸载逻辑分散且不完整；
3. 插件依赖其他服务时，需要手写初始化顺序和联动启停；
4. 后端插件与前端插件形成两套互不一致的生命周期。

统一后的基础模型是：

```python
Plugin = {
    manifest,
    activate(runtime_context, config) -> reversible effects,
}
```

Runtime 负责发现、校验、依赖协调、状态转换、effect 托管、逆序回滚和诊断。插件只声明并使用能力。

## 2. 非目标

FPR 不统一四个产品的领域模型。会议、知识条目、自动化流程和训练会话仍由各自项目拥有。

FPR 也不把所有扩展点压缩成一个无类型的 Hook。通用 Runtime 只管理生命周期；具体 Adapter 继续提供有类型的 `ActionRegistry`、`ExporterRegistry`、`KeyRegistry` 等接口。

## 3. 分层结构

```text
┌────────────────────────────────────────────────────┐
│  Plugin                                            │
│  manifest + activate(ctx, config)                  │
└───────────────────────┬────────────────────────────┘
                        │ 只调用声明过的服务/能力
┌───────────────────────▼────────────────────────────┐
│  Python SDK                                         │
│  PluginContext / EffectScope / ServiceRef / Config │
└───────────────────────┬────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────┐
│  Runtime Core                                       │
│  Catalog / Context / Graph / Reconciler / Effects  │
│  State Store Port / Diagnostics / Generation Guard │
└───────────────────────┬────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────┐
│  Host Adapter                                       │
│  AutoFlow / KnowFlow / HarvestFlow / MeetFlow       │
│  FastAPI / Registry / Outbox / Config / UI Bridge  │
└───────────────────────┬────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────┐
│  Host Application                                   │
└────────────────────────────────────────────────────┘
```

## 4. Runtime Core 的职责

Runtime Core 只拥有以下通用概念：

| 组件 | 职责 |
| --- | --- |
| `PluginCatalog` | 发现并保存经过校验的插件描述符 |
| `ContextStore` | 保存当前可用服务及其 provider generation |
| `DependencyGraph` | 建立插件到服务、provider 到 consumer 的有向图 |
| `Reconciler` | 把 Context 变化收敛成确定的生命周期转换 |
| `EffectScope` | 收集一次激活产生的 disposer，并保证只执行一次 |
| `RuntimeStateStore` | 保存 desired enabled、配置版本和故障恢复信息 |
| `DiagnosticsStore` | 暴露状态、依赖、effect 标签和脱敏错误 |

Runtime Core 禁止导入 FastAPI、SQLAlchemy、Vue、React 或具体项目模型。

## 5. 两类 Context

FPR 必须区分进程生命周期和请求生命周期。

### 5.1 Runtime Context

`activate()` 接收 `PluginRuntimeContext`。它与一个插件 activation generation 绑定，包含：

- Manifest 与插件 ID；
- 经过校验的配置快照；
- Manifest 声明过的 service 引用；
- effect API；
- capability registrar；
- 插件作用域 logger；
- Runtime 诊断接口的只读视图。

Runtime Context 不包含当前用户、HTTP Request、数据库 Session 或某个业务对象。

### 5.2 Invocation Context

Action、Hook、Exporter 或 Command 被真正调用时，Host Adapter 创建短生命周期的 `InvocationContext`，可以包含：

- actor 与授权结果；
- target type、target ID；
- trace ID、invocation ID；
- 有界业务上下文；
- Host 提供的事务或 outbox 能力。

插件禁止把 Invocation Context 存入进程级变量或 activation effect。

## 6. 服务与扩展点

FPR 将“依赖”和“扩展点”分开处理。

### 6.1 Service

Service 是动态 Context 中可被依赖的命名对象，例如：

```text
flow.logging
flow.commands
autoflow.actions
knowflow.keys
harvestflow.curators
meetflow.exporters
```

插件通过 Manifest `requires` 声明依赖，通过 `ctx.services.require()` 取得对象。未声明的服务不可访问。

插件也可以通过 `ctx.services.provide()` 提供新服务。提供服务本身是一个 effect，撤销后所有依赖者都会被重新协调。

### 6.2 Capability

Capability 是 Host 允许插件产生的一类贡献，例如注册 Action、Exporter 或 UI Slot。Manifest 必须声明具体 contribution ID，Adapter 必须校验实际注册与声明一致。

Capability registrar 的每次注册都必须自动加入当前 EffectScope。插件不能获得底层可变 Registry。

## 7. 插件入口

规范入口是一个 Python 对象：

```python
class PluginEntrypoint(Protocol):
    async def activate(
        self,
        ctx: PluginRuntimeContext,
        config: Mapping[str, Any],
    ) -> None: ...
```

也允许等价的 async function。同步函数由 SDK 包装成已完成的 awaitable，但所有 disposer 都必须同时支持同步或异步执行。

插件入口模块被导入时禁止注册 Hook、启动线程、连接外部服务或修改全局 Registry。所有副作用必须发生在 `activate()` 的 EffectScope 内。

## 8. Python 包公共边界

未来 Python 包建议采用以下边界：

```text
src/flow_plugin_runtime/
├── api.py              # 稳定公共导出
├── manifest.py         # Manifest 模型与校验
├── context.py          # Runtime/Invocation Context
├── effects.py          # EffectScope 与 Disposer
├── graph.py            # 依赖图
├── runtime.py          # Reconciler 与状态机
├── diagnostics.py      # 状态快照与错误模型
├── ports.py            # StateStore、MutationBus、Loader 等端口
└── adapters/
    ├── base.py
    └── fastapi.py
```

宿主和插件只能从 `flow_plugin_runtime.api` 导入稳定类型。其他模块均为内部实现，不承诺跨小版本兼容。

## 9. 单进程与多进程

每个 Python 进程拥有独立 Runtime、Context 和内存 Registry。启用状态和配置通过 `RuntimeStateStore` 持久化。

单进程宿主可以即时 reconcile。多 worker 或多实例宿主只有在提供 `MutationBus` 并确认所有实例应用同一配置 epoch 后，才能宣称即时启停；否则管理 API 必须返回 `restart_required: true`。

FPR 不把“某个进程已切换成功”误报为“整个部署已切换成功”。

## 10. 前端边界

Python Runtime 是唯一主运行时。第一版前端只消费后端生成的 UI Descriptor，不执行插件 Python、HTML 或 JavaScript。

Vue/React Host Bridge 不是第二套插件生命周期；它只负责：

1. 按 slot 请求已授权的 Descriptor；
2. 映射为宿主已有组件；
3. 把用户操作提交到后端 Command；
4. 隔离单个 Descriptor 的渲染错误。

详细协议见 [frontend.md](frontend.md)。

## 11. Cordis 语义映射

FPR 借鉴 Cordis 的运行时语义，但不依赖 Cordis 的 TypeScript 包：

| Cordis 概念 | FPR 概念 |
| --- | --- |
| `Context` | 动态 `ContextStore` + 插件作用域 `PluginRuntimeContext` |
| `inject` | Manifest `requires` 与只读 service snapshot |
| `provide()` | `ctx.services.provide()` service effect |
| `Fiber` | plugin activation generation + `EffectScope` |
| `effect()` | acquire 返回 disposer，Runtime 托管 |
| `notify()` | Context mutation 触发 dependency reconcile |
| provider epoch | service provider generation |
| fiber reload/unload | deactivate → reverse dispose → activate |
| HMR rollback | generation guard + 显式 HMR policy |

FPR 不复制 Cordis 的 Proxy、decorator 或 Node loader。需要保留的是“依赖变化驱动生命周期、所有副作用可撤销、旧 generation 不能污染新状态”三个不变量。

## 12. 方案决策

本规范选择“协议 + Python Runtime Core + Host Adapter”：

- 只共享 Manifest 会让四个项目再次各自实现状态机和清理，不足以保证一致性；
- 直接依赖 Cordis 会把 Python 后端绑定到 Node/TypeScript 生命周期，不适合四个现有宿主；
- Python Runtime 能被四个后端直接复用；声明式 UI 让前端无需再实现第二个插件 Runtime。

因此 Python 是生命周期权威，JSON 协议是前后端边界，Vue/React 只是被动 Host Bridge。
