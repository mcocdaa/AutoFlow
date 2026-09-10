---
title: Flow Plugin Scoped Context 规范
version: 1.0
keywords: [context, scope, isolate, intercept, service]
description: 上下文作用域与服务解析规范
---

# Scoped Context

本文件属于 `flow-plugin/v1` 核心协议，规定插件系统的空间组合语义。生命周期和 generation 见 [runtime.md](runtime.md)，父子组件见 [components.md](components.md)。

## 1. 目标

FPR 的 Context 不是一个可由插件任意修改的全局 `dict`。它必须同时满足：

- 子作用域继承父作用域可见的服务绑定；
- 一个分支可以隔离某个 Service ID，不影响其他分支；
- 父作用域可以为子树附加有界的 service binding 配置；
- 作用域销毁时，属于该作用域的组件和 effects 一起撤销；
- 插件不能借派生 Context 扩大 Manifest 权限。

这构成 FPR 的“空间维度”；[runtime.md](runtime.md) 中 dependency reconcile 和 generation 构成“时间维度”。

## 2. Context 类型

FPR 区分以下对象：

| 类型 | 生命周期 | 职责 |
| --- | --- | --- |
| `RootContext` | Python Runtime 进程 | Host Adapter、全局 service binding 和根 effect |
| `ScopedContext` | 组件子树 | 不可变的继承、隔离和 intercept 视图 |
| `PluginRuntimeContext` | 一个 component activation generation | 在 ScopedContext 上增加 Manifest、配置、effects 和 registrar |
| `InvocationContext` | 一次业务调用 | actor、target、trace、事务或 outbox |

`InvocationContext` 不是 `ScopedContext` 的子节点，不能提供服务或注册 activation effect。它只在调用已注册的 handler 时创建。

## 3. 作用域树

每个 Runtime 维护一棵 Context 树：

```text
RootContext
└── Host scope
    ├── plugin-a root component scope
    │   ├── child-x scope
    │   └── child-y isolated scope
    └── plugin-b root component scope
```

每个 `ScopedContext` 必须包含稳定的 `scope_id`、父作用域引用、service resolution key mapping 和 intercept mapping。作用域对象创建后不可原地修改；派生操作返回新作用域。

建议的公共形状是：

```python
class ScopedContext(Protocol):
    scope_id: str
    parent: "ScopedContext | None"

    def derive(self, local_id: str) -> "ScopedContext": ...

    def isolate(self, *service_ids: str) -> "ScopedContext": ...

    def intercept(
        self,
        service_id: str,
        config: Mapping[str, Any],
    ) -> "ScopedContext": ...


class ServiceView(Protocol):
    def require(self, service_id: str) -> object: ...
    def get(self, service_id: str) -> object | None: ...
```

具体实现可以使用持久化 mapping、链式对象或其他结构，但不得把父作用域暴露为可变对象。

## 4. 派生与所有权

`derive(local_id)` 创建一个继承当前解析视图的子作用域。`local_id` 只在同一父作用域内唯一，完整 `scope_id` 由 Runtime 生成，插件不得伪造。

每个非根作用域必须归属于一个父 component activation generation 的结构 effect：

1. 创建作用域不会立即激活业务组件；
2. 挂载组件后，Runtime 才把组件节点加入 desired graph；
3. 父组件退出时，Runtime 先停用整个子树，再释放父组件自身 effects；
4. 子作用域不能在父作用域销毁后继续存在；
5. 插件不得把 ScopedContext 持久化后交给其他插件或其他 Runtime。

## 5. Service Resolution Key

ContextStore 以二元组标识空间中的服务：

```text
(service_id, resolution_key)
```

根作用域为每个 Service ID 建立默认 `resolution_key`。子作用域继承父作用域的 key，因此默认情况下，不同插件可以通过同一 Service ID 互相提供和依赖服务。

服务解析固定为：

```text
consumer ScopedContext
  → 取得 service_id 对应的 resolution_key
  → 只选择相同 (service_id, resolution_key) 下的 ACTIVE provider generations
  → 应用 version 与唯一 provider 规则
  → 创建只读 service snapshot；没有匹配 provider 时 `get()` 返回 None，`require()` 产生受控的 missing dependency 错误
  → 应用 intercept binding
```

相同 Service ID 但 resolution key 不同的 provider 对当前 consumer 不可见，也不得被用于消除依赖缺失。

## 6. Isolate

`isolate(service_id)` 为当前分支生成新的不可预测 resolution key。派生作用域及其后代继承这个 key，除非后代再次 isolate。

```text
root key(flow.cache)=K0
├── plugin-a scope: K0
└── isolated scope: K1
    ├── child-provider: provide(flow.cache, K1)
    └── child-consumer: require(flow.cache, K1)
```

隔离必须遵守：

1. isolate 只改变解析域，不创建 provider；
2. 新域没有 provider 时，必需依赖保持 `INACTIVE/MISSING_DEPENDENCY`，禁止回退到外层 key；
3. isolate 不授予未在 Manifest 声明的服务访问权；
4. resolution key 只能出现在内部诊断中，不能作为稳定公共 ID 持久化；
5. 隔离分支撤销时，仅撤销该分支组件和 provider，不影响其他 key。

## 7. Intercept

`intercept(service_id, config)` 为当前分支附加 service binding 配置，用于日志字段、缓存命名空间、客户端选项等“每个 consumer 视图不同”的场景。

Intercept 不是 provider 替换，也不能改变权限、版本范围、健康状态或 provider 选择。其处理顺序固定为：

```text
选择 provider generation
  → 读取从根到当前 scope 的 intercept mapping
  → 同一 service 采用最近作用域的完整配置值
  → 使用 provider/adapter 声明的 JSON Schema 校验
  → provider binder 生成当前 consumer 的只读 service view
```

第一版采用“最近值整体替换”，不做深层 merge，避免不同 Host 得到不同结果。

Provider 必须显式声明该服务是否支持 intercept，并提供等价于以下接口的 binder：

```python
class ServiceBinder(Protocol):
    intercept_schema: Mapping[str, Any]

    def bind(
        self,
        service: object,
        config: Mapping[str, Any],
    ) -> object: ...
```

Intercept schema 属于版本化 Service ID contract，而不是某个 provider instance 的私有约定；同一兼容版本范围内的 provider 必须实现相同 schema 和 binding 语义。

对不支持 intercept 的服务设置配置、配置校验失败或 binder 执行失败时，使用该 Context 的组件保持 `INACTIVE/INVALID_INTERCEPT`。Binder 禁止注册 effect；需要资源的 consumer-specific client 必须在组件 `activate()` 中通过 `ctx.effects.acquire()` 创建。

## 8. PluginRuntimeContext 权限

`PluginRuntimeContext` 只暴露当前组件被授权的视图：

- `ctx.services.require()` 只能读取当前 component 声明为必需 `requires` 的 service；`ctx.services.get()` 只能读取 Manifest 已声明为 `optional: true` 的 service，且不建立自动 reload 的依赖边；两者都只返回 ACTIVE provider，`get()` 的结果不得跨越当前即时只读操作存活；
- `ctx.services.provide()` 只能提供 Manifest `provides` 允许的服务；
- `ctx.context.derive/isolate/intercept` 只能为当前组件的后代创建视图；
- 派生 Context 继承插件身份、权限和 capability 上限；
- child component 不能通过新的 Context 扩大 filesystem、network 或 secret 权限。

Host 可以通过 policy 禁止插件主动 isolate 某些核心 Service ID。拒绝必须发生在 child component 发布前，并产生 `PERMISSION_DENIED` 诊断。

## 9. Context Mutation 与 Reconcile

以下空间变化属于 Context Mutation：

- component scope 被挂载或撤销；
- resolution key 对应的 provider generation 出现、消失或替换；
- Host policy 改变可用隔离或 intercept 配置；
- 支持动态配置的 intercept 值产生新 epoch。

Runtime 只重新协调可能受相同 resolution key 影响的组件。实现可以做增量计算，但结果必须等价于从不可变完整 snapshot 重新计算。

ScopedContext 创建后不得原地改变。需要修改 isolate 或 intercept 时，Runtime 必须创建新 context epoch，并对相关组件执行 `deactivate → activate`。

## 10. 诊断

每个 component snapshot 至少显示：

```json
{
  "component_path": "meeting-export/preview",
  "scope_id": "scope-01J...",
  "parent_scope_id": "scope-01H...",
  "service_bindings": [
    {
      "service": "flow.logging",
      "resolution_key_ref": "key-ref-7",
      "provider_generation": 4,
      "intercepted": true
    }
  ]
}
```

诊断只能暴露不可反推内部 token 的 `resolution_key_ref`，不得输出 intercept 原始配置、service 对象或 secret。

## 11. 必测行为

实现必须验证：

- 子作用域继承默认 provider；
- isolate 分支看不到外层同名 provider；
- 隔离分支的 provider 不泄漏到兄弟分支；
- 最近 intercept 整体替换父值且不修改共享 service；
- 非法 intercept 使组件保持 INACTIVE；
- Context epoch 变化导致相关组件重载；
- 父 scope 撤销后没有存活 child、provider 或 contribution；
- 派生 Context 不能越过 Manifest 权限。
