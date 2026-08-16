---
title: Flow Plugin Host Adapter 规范
version: 1.0
keywords: [adapter, fastapi, config, event, command]
description: Python宿主适配器接口规范
---

# Host Adapter 规范

本文件定义核心协议与具体 Python 宿主之间的集成边界。

## 1. Adapter 的位置

Runtime Core 不理解 Action、会议、知识条目或审核器。Host Adapter 把项目已有 Registry、Service、权限和持久化能力包装成可逆 service/capability。

```text
Host Application
  ├─ 创建 Runtime
  ├─ 注册 HostAdapter
  ├─ HostAdapter provide 项目服务
  ├─ Runtime discover + reconcile
  └─ 应用关闭时 runtime.close()
```

## 2. 基础接口

```python
class HostAdapter(Protocol):
    id: str
    version: str

    async def install(self, host: HostContext) -> Disposer:
        """向 Runtime 提供服务、capability schema 和管理集成。"""
```

`install()` 自身也是 root runtime effect。应用关闭时先卸载所有插件，再撤销 Adapter。

Adapter 必须声明：

- 提供的 service ID 与版本；
- 支持的 capability key 和 schema；
- contribution 冲突策略；
- Invocation Context 构造方式；
- 配置、密钥、状态和事件端口；
- 是否支持即时 mutation。

## 3. Registrar

Registrar 是 Adapter 暴露给插件的受控写入口：

```python
class Registrar(Protocol):
    def register(
        self,
        contribution_id: str,
        value: object,
        metadata: Mapping[str, Any],
    ) -> EffectHandle: ...
```

实现必须：

1. 校验当前插件 Manifest 声明；
2. 校验 ID、schema、权限和冲突；
3. 从底层 Registry 取得完整注销 disposer，并立即归入当前 EffectScope；
4. 把注册归属记录为 plugin ID + generation；
5. 禁止插件取得内部 dict/list/router 的可变引用。

Registrar 只进行可快速完成的内存注册，因此是同步接口。需要 I/O 的资源建立必须使用 `ctx.effects.acquire()`，不能隐藏在 registrar 中。

## 4. 通用服务

所有宿主应当提供以下服务：

| Service ID | 说明 |
| --- | --- |
| `flow.logging` | 自动带 plugin/generation/trace 字段的日志 |
| `flow.commands` | 注册可授权调用的后端 Command |
| `flow.events` | 注册进程内事件 listener；持久事件由 outbox adapter 提供 |
| `flow.ui` | 注册声明式 UI Descriptor |
| `flow.secrets` | 按 Manifest allowlist 读取 secret |
| `flow.diagnostics` | 插件只读的自身状态和健康报告入口 |

Host 可以选择不提供某项；依赖它的插件会保持 `INACTIVE`。

## 5. Command Adapter

Command 是前端按钮、Agent 工具和后端 API 的共同调用边界：

```python
CommandHandler = Callable[
    [InvocationContext, Mapping[str, Any]],
    Awaitable[CommandResult],
]
```

注册项必须包含：

- command ID；
- target types；
- input/output JSON Schema；
- 权限策略名称；
- timeout 和 concurrency policy；
- 是否为只读、幂等或需要 invocation ID。

Adapter 调用顺序固定为：

```text
认证 → target 授权 → input 校验 → 构造 bounded context
→ handler → timeout/cancel → output 校验 → 脱敏响应
```

插件 handler 不得自行信任浏览器传入的 actor、role 或 target context。

领域 Adapter 可以把有类型 contribution 投影为 Command。例如 MeetFlow 可以把每个 Exporter 暴露成同 ID 的只读下载 Command。该投影必须固定 target 授权、输入输出校验和错误语义，UI Descriptor 只能引用已经存在的显式或投影 Command。

## 6. Event Adapter

进程生命周期事件和业务领域事件必须分开：

- `flow.events`：进程内、非持久、适合状态通知；
- Host Outbox Service：事务提交后、可重试、需要幂等的领域事件。

业务事件订阅应注册为 capability effect，但事件投递由 Host Worker 执行。插件启停只改变“当前有哪些 subscriber”，不删除 outbox 数据。

Event Handler 必须接收 `event_id`。对于非幂等交付，Host 禁止在结果不确定时自动重试；应保留 `delivery_unknown` 或等价状态。

## 7. Hook Adapter

需要 before/after Hook 的宿主必须提供有类型的 middleware chain，不允许插件 monkeypatch 原方法。

```python
HookContribution = {
    "point": "collector.parse",
    "phase": "before" | "after",
    "priority": 100,
    "handler": callable,
}
```

语义必须由 hook point 定义，例如：

- before 返回 `Continue` 或 `ShortCircuit(value)`；
- after 返回 `Keep` 或 `Replace(value)`；
- callback 按 priority 和 contribution ID 稳定排序；
- 单个 callback 错误是 fail-open 还是 fail-closed 必须由 hook point 固定，不能由插件决定。

注销 disposer 必须只移除当前 contribution。

## 8. FastAPI Adapter

第一版禁止插件直接 `app.include_router()` 或修改 `app.router.routes`。原因是动态删除路由、OpenAPI 缓存、多 worker 一致性和权限边界难以可靠协调。

FastAPI Adapter 提供稳定的通用 dispatcher：

```text
GET  /api/plugin-runtime/v1/plugins
PUT  /api/plugin-runtime/v1/plugins/{plugin_id}/enabled
PUT  /api/plugin-runtime/v1/plugins/{plugin_id}/config
POST /api/plugin-runtime/v1/plugins/{plugin_id}:retry
GET  /api/plugin-runtime/v1/ui/{slot}
POST /api/plugin-runtime/v1/commands/{command_id}:invoke
```

宿主可以改总前缀，但资源和响应语义必须保持一致。

KnowFlow 现有任意 Router 插件通过 legacy adapter 兼容；新插件必须迁移为 Command 或宿主正式资源扩展点。

## 9. 配置与状态端口

```python
class RuntimeStateStore(Protocol):
    async def snapshot(self) -> RuntimeDesiredSnapshot: ...
    async def set_enabled(self, plugin_id: str, enabled: bool) -> int: ...
    async def set_config(self, plugin_id: str, config: Mapping) -> int: ...
```

写操作返回新的单调 epoch。Runtime 只有在读到新 epoch 后才 reconcile。

Host 可以使用 YAML、SQLite 或其他数据库，但必须保证：

- 配置写入原子；
- secret 单独加密；
- 审计 actor、时间和旧/新 epoch；
- 多进程读取语义明确；
- 不把插件启停与源码安装混为同一操作。

## 10. Loader 端口

Loader 分成发现与导入两阶段：

```python
class PluginLoader(Protocol):
    async def discover(self) -> list[PluginDescriptor]: ...
    async def load(self, descriptor: PluginDescriptor) -> PluginEntrypoint: ...
```

不兼容、禁用或缺依赖的插件可以只 discover，不应提前 import。这样可以减少模块级副作用，也能在缺少可选依赖时安全展示诊断。

Loader 必须固定插件根目录并防止路径逃逸。生产环境应从只读挂载、wheel 或受控安装目录加载。

## 11. 应用启动与关闭

宿主推荐流程：

```python
@asynccontextmanager
async def lifespan(app):
    runtime = Runtime(...)
    await runtime.install(host_adapter)
    await runtime.discover()
    await runtime.reconcile()
    app.state.plugin_runtime = runtime
    try:
        yield
    finally:
        await runtime.close()
```

`runtime.close()` 必须：

1. 停止接受新 invocation；
2. 等待或取消受控 invocation；
3. 按反向依赖顺序卸载插件；
4. 撤销 Adapter root effects；
5. 输出未清理 effect 诊断。

具体项目启动仍必须遵守项目自身脚本约束；FPR 不提供绕过 `scripts/start.sh` 的启动入口。

## 12. Legacy Adapter

旧插件可以被临时包装：

```python
async def activate(ctx, config):
    async def acquire_legacy():
        await legacy.on_load()
        return legacy.on_unload

    await ctx.effects.acquire("legacy:lifecycle", acquire_legacy)
```

Legacy Adapter 只能作为迁移边界，并必须准确列出无法保证的能力，例如：

- 模块导入时已经产生副作用；
- `on_unload` 不覆盖全部注册；
- 任意 FastAPI Router 无法安全热卸载；
- 全局线程或单例无法归属 generation。

存在这些限制时，管理 API 必须显示 `restart_required` 或 `legacy_cleanup_incomplete`，不得宣称完全动态可逆。
