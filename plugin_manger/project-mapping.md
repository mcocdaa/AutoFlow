---
title: Flow 项目插件映射
version: 1.0
keywords: [autoflow, knowflow, harvestflow, meetflow, mapping]
description: 四项目现有插件映射
---

# 四个项目的能力映射

本文件描述现有代码如何映射到 FPR，不是具体迁移步骤。

## 1. 总览

| 现有项目 | 已有主要能力 | FPR 目标抽象 |
| --- | --- | --- |
| AutoFlow | Plugin、Action、Check、config/secrets | Action/Check registrar + config/secret port |
| KnowFlow | Key、Router、Hook、前端 TSX、load/unload | Key/Command/Hook registrar + UI Descriptor |
| HarvestFlow | Collector/Curator/Reviewer/Service、before/after Hook | 有类型 registrar + middleware chain + service provide |
| MeetFlow | Action、Exporter、Event Subscriber、Job、UI Slot | Command/Exporter/Outbox/UI registrar |

## 2. AutoFlow

### 2.1 当前代码事实

AutoFlow 当前从 `plugins/plugins.yaml` 读取启用项，导入模块的 `PLUGIN` 类，实例化后调用 `Plugin.register()`。`Registry` 保存 actions/checks，`get_registry()` 通过进程级 cache 初始化。当前没有 dispose，Trigger 和 UI 仍是演进方向。

### 2.2 FPR 映射

Host Adapter 提供：

```text
autoflow.actions@1
autoflow.checks@1
autoflow.artifacts@1
autoflow.flow-context@1
```

旧代码：

```python
self.actions = {"dummy.echo": self._echo}
plugin.register(registry)
```

目标语义：

```python
async def activate(ctx, config):
    actions = ctx.services.require("autoflow.actions")
    actions.register(
        "dummy.echo",
        handler=echo,
        input_schema=...,
        output_schema=...,
    )
```

`actions.register()` 自动产生删除该 Action 的 disposer。Runner 只从 Adapter 的稳定 Registry 查询 ACTIVE contribution。

`config.yaml` 中普通 defaults 进入 config snapshot；secret 名称进入 Manifest permission，值由 `flow.secrets` 提供，不再由 loader 提前解析成普通 dict。

## 3. KnowFlow

### 3.1 当前代码事实

KnowFlow Manifest 可以声明 Key、后端入口和前端入口。PluginManager 动态挂载 Router、调用 `on_load`，卸载时调用 `on_unload`、删除 Hook、Router、Key 和模块。清理逻辑由 Manager 手工知道每类资源。

### 3.2 FPR 映射

Host Adapter 提供：

```text
knowflow.keys@1
knowflow.commands@1
knowflow.item-context@1
flow.ui@1
```

Key 注册变为 effect；`delete_with_plugin` 不再表示删除用户业务数据，而只撤销 schema/展示注册。已经写入 Item 的属性值必须由 KnowFlow 的数据兼容策略保留，不能在插件卸载时静默删除。

任意 APIRouter 不进入新协议。插件操作通过 `flow.commands` 暴露，在通用 dispatcher 后执行 KnowFlow 权限校验。

现有 `frontend.tsx` 目标映射为 `knowflow.attribute-field` 等受控 Descriptor。需要复杂 TSX 的旧插件标为 legacy/restart-required，直到未来独立前端协议出现。

`on_load/on_unload` 只由 Legacy Adapter 包装；新插件只实现 `activate()`。

## 4. HarvestFlow

### 4.1 当前代码事实

HarvestFlow 通过 `plugins.yaml` 和目录类型组织插件，导入 `__init__.py` 时由装饰器注册 Hook。before Hook 可以短路，after Hook 可以链式替换；disable 会注销模块 Hook 并清理模块缓存。插件类型和初始化顺序承担隐式依赖表达。

### 4.2 FPR 映射

Host Adapter 提供：

```text
harvestflow.collectors@1
harvestflow.curators@1
harvestflow.reviewers@1
harvestflow.exporters@1
harvestflow.session-store@1
flow.hooks@1
```

Collector、Curator、Reviewer、Service 作为 capability 分类保留，不成为四套 Runtime 基类。

装饰器模块副作用：

```python
@hook_manager.hook("curator_manager_evaluate_before")
```

目标语义：

```python
async def activate(ctx, config):
    hooks = ctx.services.require("flow.hooks")
    hooks.register(
        point="curator.evaluate",
        phase="before",
        priority=100,
        handler=evaluate,
    )
```

Hook Adapter 保留 before 短路和 after 链式语义，但用显式 `Continue/ShortCircuit/Keep/Replace` 返回类型代替 `None` 的多义性。

Infisical 一类插件通过 `provides` 提供 `flow.secret-backend` service；secrets manager 对它声明 `requires`，不再依赖固定初始化顺序。

## 5. MeetFlow

### 5.1 当前代码事实

MeetFlow 已有严格 Manifest、API v1/v2、配置/密钥 schema、Action、Exporter、Event Subscriber、持久 Job/Outbox 和固定 UI Slot。加载仍是启动时批量导入 `register(registry)`，启用变化要求重启；前端模块通过动态 JavaScript import 注册组件。

### 5.2 FPR 映射

Host Adapter 提供：

```text
meetflow.actions@2
meetflow.exporters@2
meetflow.events@2
meetflow.jobs@1
meetflow.bounded-context@1
flow.ui@1
```

现有 `PluginRegistry.register_*` 改为 FPR registrar 后，Action、Exporter 和 Subscriber 的注册自动成为 effects。MeetFlow 现有 capability 校验、bounded context、JSON Schema、secret encryption、Job 和 Outbox 继续由 Host Adapter 复用。

`PluginJob` 和 `PluginEvent` 是持久业务执行状态，不属于 activation effect。禁用插件不会删除 Job/Event；Worker 在调用前检查对应 plugin generation 是否 ACTIVE。

现有前端 `frontend_entry` 在 FPR v1 中被 UI Descriptor 替代。固定 slot 设计可以直接保留，Vue `PluginSlot` 改为消费统一 Descriptor API。

## 6. 共享能力与项目能力

应当共享：

- Manifest 解析和版本兼容；
- 插件 Catalog 和 Loader；
- Context/Service 依赖图；
- Reconciler 和状态机；
- EffectScope/disposer；
- config/secret/state 端口；
- Command、UI Descriptor 和 diagnostics 基础协议；
- Contract test suite。

不得强行共享：

- 会议、知识项、会话、流程的领域模型；
- 各项目的授权规则；
- bounded context 的具体字段；
- 数据库 ORM 和迁移；
- 前端视觉组件；
- 业务 Event 类型与重试策略。

## 7. 冲突处理

四个项目已有同名但语义不同的“Hook”“Action”“Plugin”。统一时以协议语义而不是名称对齐：

- AutoFlow Action 是流程步骤 handler；
- MeetFlow Action 是用户/Job 触发的 bounded command；
- HarvestFlow before Hook 是 middleware；
- KnowFlow Router 是 HTTP surface。

它们都能成为可逆 contribution，但不会被压成同一个 handler 签名。每个 Host Adapter 保留独立类型和验证。

## 8. 兼容边界

Legacy Adapter 的目标是让旧插件在新 Runtime 中被观测和有序关闭，不是把不可逆旧实现伪装成完全兼容。

诊断必须区分：

```text
native        完全遵守 FPR effect 与依赖协议
legacy-safe   旧 ABI，但清理闭环已被验证
legacy-restart 只能启动时加载，变更需要重启
unsupported   无法满足安全或一致性要求
```

新的跨项目插件必须使用 native 协议。
