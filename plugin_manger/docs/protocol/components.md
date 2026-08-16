---
title: Flow Plugin Component 规范
version: 1.0
keywords: [component, parent, child, ownership, lifecycle]
description: 父子组件与生命周期所有权规范
---

# Component

本文件属于 `flow-plugin/v1` 核心协议，规定插件内部的声明式子组件及其生命周期所有权。Context 空间解析见 [context.md](context.md)，状态机与 effect 见 [runtime.md](runtime.md)。

## 1. Plugin 与 Component

FPR 区分安装单元和运行单元：

- **Plugin package**：Catalog 中具有 Manifest、版本和 Python 入口的安装单元；
- **Component instance**：依赖图中的运行单元，拥有独立 requires、state、generation、ScopedContext 和 EffectScope；
- **Root component**：Plugin package 的入口组件；
- **Child component**：由 ACTIVE component 声明并由父组件拥有的运行单元。

一个插件可以只有 root component。引入 child component 不是为了把所有函数组件化，而是为了表达“随父组件存在、但拥有独立依赖和可逆资源”的动态功能。

## 2. Component Spec

Child component 使用不可变声明：

```python
ComponentActivator = Callable[
    [PluginRuntimeContext, Mapping[str, Any]],
    None | Awaitable[None],
]

@dataclass(frozen=True)
class ComponentSpec:
    local_id: str
    activate: ComponentActivator
    requires: tuple[ServiceRequirement, ...] = ()
    provides: tuple[ServiceDeclaration, ...] = ()
    config_schema: Mapping[str, Any] | None = None
```

`local_id` 必须匹配插件 ID 的小写 kebab-case 规则，并且在同一父 generation 内唯一。完整 component path 由 Runtime 组成：

```text
<plugin-id>/<child-local-id>/<grandchild-local-id>
```

Component path 用于诊断和排序，不是跨卸载永久不变的数据库主键。

Root component spec 由 Manifest 的入口、必需 `requires` 和 `provides` 派生。Child spec 在 Python 中声明，但仍受 Manifest package 上限约束。

## 3. Manifest 上限

Plugin Manifest 是整个 package 的静态权限与兼容上限。Child component：

1. 只能依赖 Manifest `requires` 已列出的 Service ID；
2. 不能放宽 Manifest 的 version range；
3. `ComponentSpec.provides` 只能列出 Manifest `provides` 中 `owner: child` 已允许的服务和版本；
4. 只能注册 Manifest `capabilities` 已声明的 contribution；
5. 继承 package 的 network、filesystem 和 secret 权限，不能追加权限。

仅供可选 child 使用的服务必须在 Manifest 中声明为 `optional: true`。Child `ComponentSpec.requires` 可以把它声明为该 child 的必需依赖；服务缺失时只有 child 保持 INACTIVE，root component 不因此失活。

Runtime 必须在 child 发布前按 `config_schema` 校验并归一化 config，再生成不可变 snapshot。Schema 缺失时只允许空 mapping；配置校验失败会拒绝 mount，并使当前 parent activation 回滚。

## 4. 挂载 API

插件通过当前 generation 的受控 registrar 声明 child：

```python
class ComponentRegistrar(Protocol):
    def mount(
        self,
        spec: ComponentSpec,
        *,
        config: Mapping[str, Any] | None = None,
        context: ScopedContext | None = None,
    ) -> ComponentHandle: ...
```

`ComponentRegistrar` 由 `PluginRuntimeContext` 暴露为 `ctx.components`，因此插件调用 `ctx.components.mount(...)`。`mount()` 必须自动创建结构 effect。插件不能取得或保存 child disposer，也不实现 `unmount()`、`stop()` 或 `deactivate()`。

`ComponentHandle` 是只读诊断句柄，只能读取 component path、期望状态和当前状态；它不能强制状态转换，也不能返回 child 的可变 Context 或 EffectScope。

## 5. 发布时机

父 component activation 使用 staging scope。Child 声明的发布顺序固定为：

```text
parent ACTIVATING
  → mount child spec 到 parent staging scope
  → parent activation 成功
  → parent generation 提交为 ACTIVE
  → child desired node 发布到依赖图
  → Runtime 独立 reconcile child
```

父 activation 失败时，staging 中的 child 不得出现在公共 graph、snapshot 或 Registry 中。

父组件禁止同步等待 child ACTIVE 后才完成自己的 activation，否则会产生隐藏依赖和死锁。父组件若依赖 child 产出的服务，必须通过另一个 component 声明 service dependency，让 Runtime 处理依赖关系。

Descendant 提供的服务不能满足任何 ancestor 的 activation dependency，因为 descendant 只有在 ancestor ACTIVE 后才会发布。Root dependency resolution 必须排除同 package 的 `owner: child` candidate；没有其他可见 provider 时，root 明确保持 `MISSING_DEPENDENCY`，而不是等待一个尚未发布的 child。

## 6. Context 继承

默认情况下，child 从父 ScopedContext `derive(local_id)`，继承相同的 service resolution keys 和 intercept mappings。

父组件可以把通过 `derive()`、`isolate()` 或 `intercept()` 创建的后代 Context 传给 `mount()`。Runtime 必须验证：

- 该 Context 确实是当前父 Context 的后代；
- Context 尚未被其他 component 占用；
- Context 没有扩大父插件的权限；
- scope ID 和 component path 没有冲突。

跨插件传入 Context、挂载到祖先或兄弟 scope、复用已销毁 Context 都必须拒绝。

## 7. 独立生命周期

每个 child component 使用 [runtime.md](runtime.md) 定义的完整状态机和单调 generation。其必需依赖缺失时：

- child 为 `INACTIVE/MISSING_DEPENDENCY`；
- 父组件继续 `ACTIVE`；
- 依赖恢复后 child 自动激活；
- child 不需要父组件重新执行 `activate()`。

Child 激活失败默认只影响自身及依赖它的 consumers，不把父组件自动标为 FAILED。需要“全部或无”的功能必须建模成父组件自己的 activation effects，而不是 child。

## 8. 父子所有权

任何 ACTIVE child 都必须有 ACTIVE 的父 generation。父组件退出 ACTIVE 时顺序固定为：

```text
停止父子树接收新 invocation
  → drain/cancel 子树 invocation
  → 按反向依赖顺序 deactivate 全部 descendants
  → 确认 child services/contributions 不再可见
  → 按逆序 dispose parent 自身非结构 effects
  → 撤销 child scopes 和结构 effects
  → parent INACTIVE/FAILED/ABSENT
```

图依赖顺序优先于普通 effect 获取顺序：如果 child 消费 parent 提供的 service，必须先停 child，再撤销该 service。

父 generation 被替换时，旧 child tree 必须全部销毁。新父 generation 即使声明相同 component path，也创建新的 child generations，禁止复用旧 EffectScope 或 service snapshot。

## 9. Child 提供服务

Child 可以在其 Context resolution key 下提供 `ComponentSpec.provides` 和 Manifest `owner: child` 共同允许的服务。声明只建立依赖图候选；服务仍要等 child ACTIVE 且 `ctx.services.provide()` effect 提交后才可见。Provider 身份扩展为：

```text
(plugin_id, component_path, service_id, activation_generation)
```

服务可见范围由 [context.md](context.md) 的 resolution key 决定，而不是仅凭 component path 决定。卸载 child provider 时，Runtime 仍必须先 deactivate 所有匹配该 provider generation 的 consumers。

## 10. 动态集合

Component 数量可以由已校验配置决定，例如为每个 workspace 创建一个隔离 worker，但必须满足：

- local ID 来自稳定、规范化的标识，不包含 secret 或用户显示名；
- Host policy 设置每个 plugin 和 parent 的 component 数量上限；
- 同一 config epoch 对相同输入产生确定的 component specs；
- 配置变化通过父 generation reload 重建集合，禁止原地修改 child spec；
- 不得根据单次 HTTP 请求挂载进程级 child，短期工作应使用 Invocation/Job。

## 11. Effect Tree

Component tree 和 effect tree 是相关但不同的诊断结构：

```text
plugin root component
├── effects
│   ├── service:plugin.cache
│   └── command:plugin.refresh
└── child component:worker
    ├── effects
    │   └── watcher:source
    └── child component:metrics
```

每个 component 有自己的 EffectScope。普通 nested EffectScope 只组织同一 component 的资源，不拥有独立依赖状态；child component 才是依赖图节点。

## 12. 错误与诊断

稳定错误至少包括：

```text
duplicate_component
invalid_component_context
component_limit_exceeded
component_parent_inactive
```

Runtime snapshot 必须能按 tree 返回：component path、parent path、scope、state、reason、generation、requires、providers 和 effect labels。普通用户接口可以只显示 root 汇总状态，但管理员诊断不得隐藏 FAILED child。

## 13. 必测行为

实现必须验证：

- 父 activation 失败时 child 从未发布；
- child 缺依赖不影响父 ACTIVE；
- 依赖恢复时只激活相关 child；
- child activation 失败完成自身 rollback；
- 父退出时 descendants 在父 effects 前完成 deactivation；
- 父 generation 替换后无旧 child/effect/service 残留；
- 重复 local ID、跨树 Context 和超限动态集合被拒绝；
- component/service 依赖环进入可解释的 `DEPENDENCY_CYCLE`。
