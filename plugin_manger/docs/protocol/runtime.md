---
title: Flow Plugin Runtime 生命周期规范
version: 1.0
keywords: [lifecycle, reconcile, effect, rollback, state]
description: 插件状态机与可逆效果规范
---

# Runtime 生命周期

本文件属于 `flow-plugin/v1` 核心协议。

## 1. 状态模型

Runtime 对每个 component instance 暴露以下状态。Plugin 的公共状态是 root component 状态及 child tree 摘要：

| 状态 | 含义 |
| --- | --- |
| `ABSENT` | Root 不在 Catalog，或 child desired spec 尚未发布/已撤销 |
| `INACTIVE` | 已发现但当前不能或不应激活 |
| `ACTIVATING` | 正在创建新的 activation generation |
| `ACTIVE` | 当前 generation 已提交并可对外提供能力 |
| `DEACTIVATING` | 正在撤销当前 generation 的 effects |
| `FAILED` | 激活或撤销未能安全完成，需要新变化或人工重试 |

`INACTIVE` 必须附带 reason：

```text
DISABLED
MISSING_DEPENDENCY
AMBIGUOUS_PROVIDER
DEPENDENCY_CYCLE
INVALID_CONFIG
INVALID_INTERCEPT
PERMISSION_DENIED
INCOMPATIBLE_HOST
INCOMPATIBLE_ADAPTER
DEPENDENCY_FAILED
```

状态和 reason 分离，避免为每个原因扩展状态机。

`FAILED` 使用 `ACTIVATION_FAILED`、`CLEANUP_FAILED`、`RELOAD_FAILED` 或 `ROLLBACK_FAILED` reason，并保留脱敏错误引用。

## 2. 状态转换

```text
ABSENT
  │ discover
  ▼
INACTIVE ── dependencies ready ──▶ ACTIVATING ── commit ──▶ ACTIVE
   ▲                                  │                       │
   │                                  └─ failure ─▶ FAILED    │
   │                                                          │
   └──────────── rollback complete ◀── DEACTIVATING ◀─────────┘
                                           │
                                           └─ cleanup failure ─▶ FAILED
```

从 `FAILED` 只允许以下事件触发新协调：

- Manifest 或代码 generation 变化；
- 配置或依赖 generation 变化；
- 管理员显式 retry；
- 进程重启并重新发现。

Runtime 禁止对未知结果的激活或外部副作用进行无条件自动重试。

## 3. Context Mutation

以下事件都属于 Context Mutation：

- 插件被发现、安装、移除、启用或禁用；
- 配置 epoch 改变；
- provider service 提供、撤销、替换或健康状态改变；
- ScopedContext 被创建、撤销或产生新 context epoch；
- child component 被挂载或由父 generation 撤销；
- Host Adapter 出现或消失；
- 权限 grant 改变；
- 插件代码 generation 热替换。

Mutation 只负责更新 desired snapshot，然后向单一 reconcile 队列发信号。多个连续 mutation 必须被合并，禁止并发执行多轮图协调。

## 4. 依赖图

图包含三类节点：component instance、scoped service binding 和 ACTIVE provider generation。Component 可以是 Plugin root，也可以是 parent-owned child：

```text
provider component ──declares──▶ scoped service binding
consumer component ──requires──▶ scoped service binding
ACTIVE provider generation ──realizes──▶ scoped service binding
```

Scoped service binding 由 `(service_id, resolution_key)` 标识。Host provider candidate 来自 Adapter service declaration；Plugin root candidate 来自 Manifest `provides owner: root`；child candidate 来自 `ComponentSpec.provides` 与 Manifest `owner: child` 的交集。

provider generation 由 `(plugin_id, component_path, service_id, activation_generation)` 唯一标识。即使服务对象相等，generation 改变也视为替换。声明的 candidate 只用于建图和环检测；只有 ACTIVE generation 的实际 provide effect 才能满足依赖。Provider 和 consumer 必须指向相同 scoped binding；详见 [context.md](context.md)。

Runtime 必须：

1. 用强连通分量检测必需依赖环；
2. 让环内插件保持 `INACTIVE/DEPENDENCY_CYCLE`；
3. 按稳定拓扑顺序激活；
4. 按反向拓扑顺序先卸载 consumer，再卸载 provider；
5. 父 component 退出前先卸载全部 descendants；
6. 使用 component path 作为同层稳定排序，保证测试和诊断可重复。

## 5. Reconcile 算法

每轮 reconcile 使用不可变 snapshot：

```text
1. 读取 catalog、desired enabled、code/config/context epochs、component specs 和 service generations
2. 校验 compatibility、permissions、config 和依赖
3. 标记必须退出 ACTIVE 的 components
4. 按反向拓扑 deactivation 并等待完成
5. 重新计算可用 provider generations
6. 标记可以进入 ACTIVE 的 components
7. 按正向拓扑 activation 并等待完成
8. 发布 RuntimeSnapshot 和 transition events
9. 如果过程中收到新 mutation，从最新 snapshot 再运行一轮
```

单轮内不得让同一 component 同时处于 activation 和 deactivation。父子发布与撤销还必须遵守 [components.md](components.md) 的结构所有权顺序。

## 6. Activation Generation

每个 component 每次激活生成单调递增的 `generation`。所有异步完成、service provide 和 diagnostics 都必须携带 component path 与 generation。

如果旧 generation 的异步工作在新 generation 建立后返回，Runtime 必须忽略其发布结果，并立即调用它产生的 disposer。这样可防止慢连接、慢导入或慢配置覆盖新状态。

## 7. Effect 模型

Effect 是一次可撤销资源获取：

```python
Disposer = Callable[[], None | Awaitable[None]]

class EffectScope(Protocol):
    def nest(self, label: str) -> "EffectScope": ...

    def own(
        self,
        label: str,
        disposer: Disposer,
    ) -> EffectHandle: ...

    async def acquire(
        self,
        label: str,
        factory: Callable[[], Disposer | Awaitable[Disposer]],
    ) -> EffectHandle: ...
```

`nest()` 返回由当前 scope 自动拥有的子 scope，用于组织同一 component 的多组资源。`EffectHandle` 和 nested scope 都不向插件提供跳过 Runtime 状态机的公开 dispose/close 操作。

所有 registrar 必须在内部使用当前 EffectScope。例如：

```python
ctx.actions.register("plugin.action", handler)
```

对于同步 Registry，它等价于：

```python
ctx.effects.own(
    "action:plugin.action",
    action_registry.add("plugin.action", handler),
)
```

其中 `action_registry.add()` 返回删除该 Action 的 disposer。

需要异步建立的连接、watcher 或客户端使用 `acquire()`；已经取得 disposer 的同步注册使用 `own()`。两者进入同一个逆序清理栈。

FPR v1 的 effect factory 只返回一个 disposer，不接受 disposer iterable、async generator 或任意对象。一次 acquisition 创建多项资源时，插件必须逐项 `own()`，或先 `nest()` 再在子 scope 中 acquire，使失败点和撤销顺序保持明确。

## 8. Effect 所有权

每个 effect 必须满足：

1. 归属于一个 plugin ID、component path 和 activation generation；
2. 有稳定、可脱敏的 label；
3. 成功 acquire 后返回 disposer；
4. disposer 最多执行一次；
5. disposer 可重复被请求，但第二次必须为空操作；
6. 不允许把 disposer 交给插件自行保存和选择性调用；
7. Runtime 可查询 effect tree，但不能暴露敏感资源值。
8. acquire factory 在返回 disposer 前若失败，必须自行清理已取得的部分资源；Runtime 无法撤销一个从未交付的 disposer。

嵌套 scope 形成同一 component 内的 effect tree。父 scope 撤销时，子 scope 先撤销。Nested EffectScope 不拥有独立依赖状态；需要独立 requires/state/generation 时必须声明 child component，而不是伪装成 nested effect。

## 9. 激活事务

Activation 使用 staging scope：

```text
创建 generation
  → 校验并导入入口
  → 调用 activate
  → acquire effects 到 staging scope
  → 全部成功
      → 提交 service provides 和 capabilities
      → state = ACTIVE
  → 任一失败
      → staging effects 逆序 rollback
      → state = FAILED
```

对内存 Registry 和 service provide，Adapter 应当先 staging，再原子发布。无法 staging 的外部资源允许先创建，但必须在激活失败时立即撤销。

只有 `ACTIVE` generation 提供的 service 才能满足 consumer 依赖。

## 10. 撤销顺序

Runtime 在三个层次保证逆序：

1. 结构层次：descendant component 在 parent 之前撤销；
2. 图层次：consumer 在 provider 之前撤销；
3. component 层次：同一 generation 的 effects 按 acquire 的逆序撤销。

同一 component 的 disposer 默认顺序 await，前一个完成后才执行下一个；只有显式创建的独立 nested EffectScope 才可以由 Runtime 并行清理。

示例：

```text
acquire: database client → timer → event subscription
dispose: event subscription → timer → database client
```

每个 disposer 异常必须记录，但 Runtime 继续撤销剩余 effects。全部执行后若仍有 cleanup error，状态进入 `FAILED`，reason 为 `CLEANUP_FAILED`，禁止在同进程内盲目重新激活。

## 11. 动态依赖

Service provide effect 提交后，ContextStore 在当前 `(service_id, resolution_key)` 发布新 provider generation；撤销前先触发匹配 consumers deactivation，等 consumers settled 后才删除 provider service。

依赖恢复时 Runtime 自动重新激活 consumer。插件不需要监听“服务上线/下线”事件。

可选依赖默认不阻止激活，但 `reload_on_change: true` 时，它的出现、消失或替换会触发 consumer reload，使插件获得新的不可变 service snapshot。

## 12. Service 健康状态

Runtime 不自行轮询数据库、网络或第三方服务。Provider 或 Host Adapter 通过明确 mutation 报告 `READY/UNAVAILABLE`。

为避免抖动：

- Host 可以在上报前做 debounce/hysteresis；
- Runtime 合并同一 reconcile 窗口内的 mutation；
- 同一 service epoch 重复状态不得触发 reload。

## 13. 配置更新

配置更新流程固定为：

```text
校验新配置
  → 持久化为新 config epoch
  → mutation
  → deactivation 旧 generation
  → activation 新 generation
```

如果新 generation 激活失败，Runtime 默认保持 `FAILED` 并保留旧配置值用于审计，但不自动恢复旧 ACTIVE generation。Host 可以提供显式的“回滚配置”命令，回滚本身产生新的 config epoch。

这避免“管理 API 返回失败但旧/新插件实际状态不确定”。

## 14. 启用、禁用和移除

- 禁用：desired enabled 变为 false，执行完整 deactivation，最终 `INACTIVE/DISABLED`。
- 启用：desired enabled 变为 true，进入依赖协调，不保证立即 ACTIVE。
- 移除：必须先完成 deactivation，再从 Catalog 删除并进入 `ABSENT`。
- 热替换：以整个 Plugin package 和 component tree 为单位，使用 loader checkpoint、显式 policy 和新 generation 执行补偿事务。

第一版默认不启用生产 HMR。开发 HMR 的 prepare、switch、cleanup 和 rollback 必须遵守 [hot-reload.md](hot-reload.md)，不得只做原地 `importlib.reload()`。

## 15. 永久业务写入不是 Effect

发送邮件、扣款、发布内容、写业务记录等不可逆操作禁止发生在 `activate()` 中。这些动作必须位于 Action/Command/Event Handler，并使用宿主的事务、幂等键或 outbox。

Effect 只适合进程资源与注册关系，例如：

- 注册或注销 Action、Hook、Exporter、UI Descriptor；
- 开关 timer、watcher、线程和连接池；
- provide/remove service；
- 创建和关闭临时客户端。

插件永久数据不得依赖 disposer 删除，否则会把插件卸载错误地变成业务数据删除。
