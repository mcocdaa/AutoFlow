---
title: Plugin SDK 规范
description: AutoFlow 插件扩展边界框架级规范
keywords: [plugin, sdk, 规范, 扩展, 边界]
version: "2.0"
---

# Plugin SDK 规范（框架级）

本文档定义 AutoFlow 的插件扩展边界：插件如何声明能力、如何被加载、如何扩展 Action/Check，以及如何进行最小权限的安全控制。

插件的业务说明与实现细节应放在各插件目录内（例如 `plugins/<plugin>/README.md`），不写进 `docs/`；插件开发的操作性指南见 `docs/zh/plugin-dev-guide.md`。

## 插件能力模型

插件可以扩展以下能力（可按需实现）：

- **ActionType**：新增动作类型与参数 schema
- **CheckType**：新增校验类型与参数 schema

（Trigger 与 UI 配置面板为框架演进方向，当前未实现。）

## 最小接口（抽象）

框架只依赖以下抽象概念：

- **`Plugin` 基类**（`plugins/common/plugin.py`）：声明式元信息 `name` / `version` / `actions` / `checks` 类属性 + 统一 `register()` 实例方法
- **`PLUGIN` 导出约定**：插件模块导出 `PLUGIN = XxxPlugin`（类引用），由 loader 实例化并注入 config
- **`ActionHandler` / `CheckHandler`**（`app.core.registry`）：action/check 的实现签名

```python
class Plugin:
    name: str
    version: str = "0.1.0"
    actions: dict[str, ActionHandler] = {}
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None: ...
    def register(self, registry: Registry) -> None: ...
```

约定：

- `version` 建议遵循语义化版本。
- handler 必须为模块级函数或 `@staticmethod`（类体内无法引用实例方法）。
- `config` 由 loader 从插件目录 `config.yaml` 解析注入：`defaults` 原样传入，`secrets` 块解析为环境变量值；无 `config.yaml` 时传 `None`。

## Schema 与校验

**演进方向（当前未实现）**：插件为每个扩展点提供参数 schema（例如 JSON Schema），用于校验 Flow 中的 `params`。

框架应保证：

- schema 校验失败时，能定位到具体文件/字段/原因
- 未安装对应插件时，能提示缺失的 `type`

当前阶段，`params` 校验由插件 handler 内部完成（必填参数缺失时 `raise ValueError`，Runner 转为步骤失败）。

## 生命周期（实际机制）

- `load`：`plugin_loader` 读取 `plugins.yaml` 启用的插件并导入模块
- `init`：识别 `PLUGIN` 类引用，实例化并注入 config（即构造阶段）
- `register`：调用 `plugin.register(registry)` 注册插件元信息、actions、checks
- `dispose`：当前框架未实现（插件为进程内单例，`get_registry` 经 `lru_cache` 缓存）

## 安全边界（框架要求）

- **Secrets 不明文**：插件只能通过 `config.yaml` 的 `secrets` 块引用环境变量访问凭证，严禁把凭证写入 Flow/插件代码。
- **最小权限**：网络域名白名单、文件路径白名单等由插件自行声明与校验（如 `openclaw` 的 `allowed_commands` 白名单、helpers 的 `read_text` 防目录穿越）。
- **产物脱敏**：日志与产物必须支持脱敏规则（由插件自行处理敏感字段，框架未统一实现）。
