---
title: Flow Plugin Hot Reload 规范
version: 1.0
keywords: [hot-reload, hmr, transaction, rollback, generation]
description: 插件热替换与回滚规范
---

# Hot Reload

本文件属于 `flow-plugin/v1` 核心协议，规定代码 generation 热替换的补偿事务。它不承诺 Python 模块真正卸载，也不承诺零停机。

## 1. 基本原则

热替换必须遵守：

1. 新代码先 prepare，旧 generation 后退出；
2. 旧代码必须有可重新激活的 checkpoint；
3. 新旧 effects、services 和 contributions 不得同时对外可见；
4. 新代码失败时，先完整清理新 generation，再决定是否恢复旧代码；
5. 恢复旧代码也创建新 activation generation，禁止复活旧 EffectScope；
6. 任一步结果不确定时 fail closed，不得宣称 rollback 成功。

生产环境默认禁用热替换。禁用时，代码变化只能产生 `restart_required`，不能隐式修改运行状态。

## 2. Reload Unit

热替换的最小单位是一个 Plugin package，包括：

- Manifest 与入口对象；
- root component；
- 该 root generation 拥有的全部 child component；
- package 提供的 services、capabilities 和 UI Descriptors。

禁止只替换某个 class/function 并保留旧 component tree，也禁止把新代码注入仍在执行的旧 handler。

## 3. Code Epoch

Loader 为每个已准备的代码版本分配单调 `code_epoch`，并记录不可变 `code_digest`。Activation generation 必须引用精确 code epoch：

```text
plugin_id + code_epoch + config_epoch + context_epoch
  → activation generation
```

收到文件变化不等于 code epoch 已提交。只有 candidate prepare 成功并进入切换流程后，Runtime 才能把它作为目标 epoch。

## 4. Policy

Host 必须为每个环境选择显式策略：

| Policy | 行为 |
| --- | --- |
| `DISABLED` | 不热替换，报告 `restart_required` |
| `FAIL_CLOSED` | 新代码失败后保持插件 FAILED，不恢复旧代码 |
| `ROLLBACK` | 新代码失败且清理成功后，尝试重新激活 checkpoint 中的旧代码 |

默认值固定为：生产 `DISABLED`，开发环境可以显式选择 `ROLLBACK`。不得根据异常类型临时改变 policy。

## 5. Loader 事务端口

Loader 必须提供等价的准备、提交、放弃和恢复边界：

```python
class ReloadCandidate(Protocol):
    descriptor: PluginDescriptor
    entrypoint: PluginEntrypoint
    code_epoch: int
    code_digest: str


class ReloadCheckpoint(Protocol):
    descriptor: PluginDescriptor
    entrypoint: PluginEntrypoint
    code_epoch: int
    code_digest: str


class TransactionalPluginLoader(Protocol):
    async def capture_checkpoint(
        self,
        current: PluginDescriptor,
    ) -> ReloadCheckpoint: ...

    async def prepare_reload(
        self,
        current: ReloadCheckpoint,
    ) -> ReloadCandidate: ...

    async def commit(self, candidate: ReloadCandidate) -> None: ...
    async def discard(self, candidate: ReloadCandidate) -> None: ...
    async def restore(self, checkpoint: ReloadCheckpoint) -> PluginEntrypoint: ...
```

`capture_checkpoint()` 必须在任何旧 generation deactivation 之前完成；`prepare_reload()` 接收的 `current` 就是本次事务保存的旧 checkpoint。实现可以使用独立 module namespace、版本化 wheel、受控 import cache 或其他机制，但必须保证 checkpoint 在事务结束前仍可加载。单纯覆盖源文件后调用 `importlib.reload()`，却无法恢复旧入口，不符合 `ROLLBACK` policy。

入口模块仍必须遵守“导入阶段无副作用”。Prepare 阶段产生不可撤销副作用必须视为 `reload_prepare_failed`。

## 6. 操作状态

Reload operation 使用独立状态，不扩展 component 生命周期状态：

```text
IDLE
  → PREPARING
  → SWITCHING
  → SUCCEEDED
      or ROLLING_BACK → ROLLED_BACK
      or FAILED
```

PREPARING 期间旧 generation 保持 ACTIVE。进入 SWITCHING 后会出现短暂不可用窗口，因此 FPR 不宣称零停机。

Prepare 失败只使 reload operation 进入 FAILED，旧 component tree 继续 ACTIVE；不能把它误报成插件运行故障。只有进入 SWITCHING 后无法恢复一致状态时，插件才进入生命周期 `FAILED`。

## 7. ROLLBACK 流程

`ROLLBACK` policy 的固定流程是：

```text
1. serialize reload request and capture old checkpoint through `capture_checkpoint()`
2. prepare candidate in isolated loader state
3. validate Manifest, compatibility, permissions and entrypoint
4. stop accepting new invocations for the old component tree
5. drain/cancel bounded invocations
6. deactivate the complete old component tree
7. if cleanup failed: discard candidate → FAILED
8. activate candidate into a new staging generation without publishing it
9. if staging succeeded: commit Loader candidate, then atomically publish the generation
10. only after Loader and Runtime commits both succeed: SUCCEEDED
11. if activation or commit failed: stop candidate invocation and rollback all candidate effects
12. if candidate cleanup failed: FAILED, do not restore old code
13. restore old checkpoint through Loader
14. activate old entrypoint with another new generation
15. if old activation succeeded: ROLLED_BACK
16. otherwise: FAILED with rollback_failed
```

`ROLLED_BACK` 表示“旧代码已作为新 generation 重新激活”，不表示从未发生过中断。原旧 generation 在第 6 步后永久结束。

Runtime 的 generation publish 必须是经过预校验、不会执行插件代码的内存提交。Loader commit 后若 publish 仍失败，Runtime 必须先撤销 candidate，再恢复 checkpoint；该失败不得留下对外可见的半提交 generation。

Candidate root 成功提交后，child components 按普通 reconcile 语义重新创建。非关键 child 失败只影响自身及其 consumers，不把已经成功的 package reload 自动改判为回滚；需要原子成功的功能必须放在 root activation transaction 内。

## 8. FAIL_CLOSED 流程

`FAIL_CLOSED` 与上述流程相同，直到 candidate 激活失败并完成清理。随后插件进入 `FAILED/RELOAD_FAILED`，旧 checkpoint 只用于审计，不重新激活。

管理员可以在修复代码后显式 retry，也可以执行显式的“恢复 checkpoint”管理操作；后者是新的 reload transaction，不是原操作的延续。

## 9. Cleanup Failure

以下任一情况都禁止继续自动切换：

- 旧 generation 存在未清理 effect；
- candidate rollback 存在未清理 effect；
- invocation drain/cancel 超时且 handler 仍可能写入旧状态；
- Loader 无法判断 candidate 是否已提交；
- 多进程实例对 code epoch 的确认结果不一致。

Runtime 必须进入 FAILED，保留残留 effect 标签、checkpoint ref 和脱敏错误。未知结果不得自动重试，也不得并行启动旧或新 generation。

## 10. 快速连续变化

同一 plugin 的 reload 必须串行。PREPARING 前可以合并多个文件事件，只保留最新目标；进入 SWITCHING 后不得取消当前事务。

切换期间收到更新时：

1. 记录更高 desired code epoch；
2. 先让当前事务 settle 为 SUCCEEDED、ROLLED_BACK 或 FAILED；
3. SUCCEEDED 或 ROLLED_BACK 后仍存在更新时，开始下一事务；
4. PREPARING 阶段失败且旧 component tree 仍 ACTIVE 时，只有更高 code epoch 或管理员显式 retry 才能开始新事务；
5. SWITCHING/ROLLING_BACK 阶段失败并使 component 进入生命周期 FAILED 时，禁止自动开始下一事务，必须遵守 Runtime 的 FAILED retry gate。

不同 plugin 可以并行 prepare，但涉及相同 provider/consumer 子图的 SWITCHING 必须进入 Runtime 的单一 reconcile 序列。

## 11. Context 与 Component

Reload 必须重建整个 component tree：

- 旧 ScopedContext 和 child handles 在旧 generation 结束后失效；
- 新 root component 从当前 Host context snapshot 派生新 scope；
- isolate/intercept 声明重新计算并产生新的 context epoch；
- 旧 child path 可被新 tree 复用作诊断路径，但 generation 和 scope ID 必须不同；
- 依赖 candidate services 的外部 consumers 只能在 candidate ACTIVE 后重新协调。

## 12. 多进程

多 worker/多实例环境只有具备 code artifact 分发、MutationBus 和 epoch acknowledgment 时才能启用热替换。控制面必须区分：

```text
prepared_instances
switched_instances
rolled_back_instances
failed_instances
```

任一实例失败时，Host policy 可以执行部署级补偿，但单进程 Runtime 不得把局部成功报告为全局成功。没有协调器时必须返回 `restart_required: true`。

## 13. 诊断与审计

每次 reload 至少记录：

```json
{
  "reload_id": "reload-01J...",
  "plugin_id": "meeting-export",
  "policy": "ROLLBACK",
  "from_code_epoch": 8,
  "target_code_epoch": 9,
  "result_code_epoch": 8,
  "operation_state": "ROLLED_BACK",
  "failure_phase": null,
  "component_state": "ACTIVE",
  "old_generation": 21,
  "candidate_generation": 22,
  "restored_generation": 23,
  "checkpoint_ref": "checkpoint-...",
  "error_ref": "diag-..."
}
```

审计不得记录源码内容、模块全局变量、secret 或 service 对象。

## 14. 必测行为

实现必须验证：

- prepare 失败时旧 generation 持续 ACTIVE；
- 新代码成功时旧 effects 和 child tree 全部撤销；
- candidate activation 部分失败会逆序 rollback；
- `ROLLBACK` 下恢复的是新 generation，不是旧 scope；
- candidate cleanup 失败时不会并行恢复旧代码；
- 旧代码恢复失败产生 `rollback_failed`；
- 连续变化被合并或串行，不发生 generation 交叉发布；
- `DISABLED` 和无协调多进程返回 restart-required；
- snapshot 能区分 SUCCEEDED、ROLLED_BACK 和 FAILED。
