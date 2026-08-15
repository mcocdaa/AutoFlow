---
title: 插件开发指南
description: AutoFlow 插件开发指南(Plugin 基类 ABI)
keywords: [插件, plugin, 指南, sdk, 开发]
version: "2.0"
---

# AutoFlow 插件开发指南

本文档是 AutoFlow 插件开发的完整指南，针对团队内部开发者。通读本文档即可掌握插件开发的核心概念。

## 目录

- [1. 快速入门](#1-快速入门)
- [2. Plugin 基类](#2-plugin-基类)
- [3. Action 开发规范](#3-action-开发规范)
- [4. Check 开发规范](#4-check-开发规范)
- [5. 共享工具(plugins/common/helpers.py)](#5-共享工具pluginscommonhelperspy)
- [6. 配置与 Secrets(config.yaml)](#6-配置与-secretsconfigyaml)
- [7. 注册表与插件加载](#7-注册表与插件加载)
- [8. 现有插件示例分析](#8-现有插件示例分析)

## 1. 快速入门

### 最小插件结构

所有 AutoFlow 插件都是一个目录（或单个 `.py` 文件），包含以下文件：

```
插件目录/
├── __init__.py       # 包入口（导出 PLUGIN）
├── backend.py        # class XxxPlugin(Plugin)，actions/checks 在 __init__ 中绑定实例方法
└── config.yaml       # 可选，defaults + secrets（secrets 由 loader 解析为环境变量值）
```

目录插件必须包含 `__init__.py`，并被 `backend/app/runtime/plugin_loader.py` 以 `plugins.<目录名>` 导入。文件插件（如 `plugins/examples/*.py`）直接在单文件中定义 Plugin 子类并导出 `PLUGIN`。

### 完整最小示例

对应文件 `plugins/dummy/backend.py`：

```python
# @file /plugins/dummy/backend.py
# @brief Dummy 插件：回传用户输入信息（测试用）

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class DummyPlugin(Plugin):
    """Dummy 插件：回传用户输入信息（测试用）"""

    name = "dummy"
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "dummy.echo": self._echo,
        }
        self.checks = {}

    def _echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


PLUGIN = DummyPlugin
```

`__init__.py` 只需导出 `PLUGIN`：

```python
# @file /plugins/dummy/__init__.py
# @brief Dummy 插件入口

from plugins.dummy.backend import PLUGIN

__all__ = ["PLUGIN"]
```

在 `plugins/plugins.yaml` 中登记插件后即可被加载：

```yaml
plugins:
  dummy:
    enabled: true
```

## 2. Plugin 基类

`Plugin` 基类位于 `plugins/common/plugin.py`，提供声明式元信息、统一注册与配置/dry_run/错误共性 API（替代旧版注册样板）：

```python
class Plugin:
    """插件基类：声明式元信息 + 统一注册 + 配置/dry_run/错误共性 API"""

    name: str
    version: str = "0.1.0"
    dry_run_env: str | None = None   # 可选：部署级 dry_run 环境变量名

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))
        self.secrets = dict(self.config.get("secrets", {}))
        self.actions: dict[str, ActionHandler] = {}
        self.checks: dict[str, CheckHandler] = {}

    def register(self, registry: Registry) -> None:
        """注册 plugin 元信息、actions、checks"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)
```

关键规则：

- **`name`**：插件唯一标识，与 plugins.yaml 的 key 解耦（但建议一致）。
- **`version`**：插件版本号，默认 `"0.1.0"`。
- **`dry_run_env`**（可选）：部署级 dry_run 开关的环境变量名，作为 `is_dry_run()` 判定链的第三级。
- **`actions` / `checks`**：**实例属性**，在 `__init__` 中绑定 `类型名 -> 实例方法` 的映射（handler 签名 `def _xxx(self, ctx, params)`，必须调用 `super().__init__(config)` 后初始化）。
- **`__init__(config)`**：loader 会把 `config.yaml` 的解析结果注入构造（无 config.yaml 时传 `None`）；基类已将 `defaults` / `secrets` 归一为实例属性 `self.defaults` / `self.secrets`。
- **`register()`**：由基类实现，插件**无需编写**。
- **`PLUGIN = XxxPlugin`**：模块必须导出 `PLUGIN`（类引用，非实例），loader 据此识别。

类型名规则为 `插件名.功能`，例如：`zhihu.fetch_answer`、`desktop.click`。

### 基类共性 API

所有插件可直接使用以下基类方法：

- **`is_dry_run(ctx, params) -> bool`**：统一 dry_run 判定，判定链 `params["dry_run"]` → `ctx.vars["dry_run"]` → 环境变量 `dry_run_env`。
- **`setting(params, key, *, env_var=None, default=None) -> Any`**：统一取值链 `params[key]` → `self.defaults[key]` → `self.secrets[key]` → `os.getenv(env_var)` → `default`；值支持 `env:VAR` 形式（自动解析为环境变量值）。
- **`error_result(error, *, error_type="unknown_error", **fields) -> dict`**：统一错误返回构造，结果为 `{"error": ..., "error_type": ..., **fields}`。

## 3. Action 开发规范

### ActionHandler 接口

```python
ActionHandler = Callable[[ActionContext, dict[str, Any]], Any]
```

其中：

- `ActionContext`：上下文信息（见下）
- `dict[str, Any]`：参数字典（Flow 中 `params` 段，已解析模板）
- 返回值：任意数据结构（将作为下一步的 `input`）

在类方法形态下，handler 是插件类的**实例方法**，签名 `def _xxx(self, ctx: ActionContext, params: dict[str, Any]) -> Any`，在 `__init__` 中绑定到 `self.actions`。

### ActionContext 包含哪些信息

```python
@dataclass(frozen=True)
class ActionContext:
    run_id: str              # 流程 ID
    step_id: str             # 步骤 ID
    input: Any | None        # 上一步输入
    vars: dict[str, Any]     # 变量字典
    artifacts_dir: Path      # 产物目录
```

常用的内容包括：

- `input`：上一步的输入数据
- `vars`：全局变量，可以从中读取配置信息
- `artifacts_dir`：存储产物的目录，一般建议在此目录下创建子目录

### 返回值格式

Action 的返回值不限定，但建议返回包含关键信息的字典：

```python
return {
    "result": True,           # 执行结果
    "data": 处理后的数据,     # 具体数据
    "message": "成功执行",     # 人可读的信息
    "dry_run": False,        # 是否为模拟模式（可选）
}
```

### 参数校验与错误

- 必填参数缺失时 `raise ValueError("xxx is required")`，Runner 会把异常转为步骤失败并记录 error。
- 可选参数用 `params.get("key", 默认值)` 读取。

## 4. Check 开发规范

### CheckHandler 接口

```python
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]
```

其中：

- `CheckContext`：上下文信息（见下）
- `dict[str, Any]`：检查参数
- 返回值：`True` / `False` 标识检查结果

### CheckContext 包含哪些信息

```python
@dataclass(frozen=True)
class CheckContext:
    run_id: str               # 流程 ID
    step_id: str              # 步骤 ID
    action_output: Any | None # 上一步 Action 输出
    vars: dict[str, Any]      # 变量字典
```

常用的内容包括：

- `action_output`：上一步 Action 的返回值，可以根据这些数据进行检查
- `vars`：全局变量

### 返回 True/False

```python
return True   # 检查通过
return False  # 检查失败
```

检查失败时 Runner 会将步骤标记为失败，无需抛出异常。

## 5. 共享工具(plugins/common/helpers.py)

插件间的通用工具已收敛到 `plugins/common/helpers.py`，直接复用，不要复制粘贴：

| 函数 | 说明 |
|------|------|
| `is_truthy(v)` | 宽松布尔化：None/空串 为 False，`"1"/"true"/"yes"` 等为 True |
| `resolve_env_value(value)` | 若 value 为 `env:VAR` 形式则解析为环境变量值，否则原样返回 |
| `error_result(error, *, error_type="unknown_error", **fields)` | 统一错误返回构造（基类 `error_result` 的纯函数版） |
| `read_text(ctx, path, extra_roots=())` | 安全路径读取（防目录穿越，默认允许 artifacts_dir 与仓库根） |
| `write_text(ctx, rel_path, text)` | 写入 artifacts 目录，返回相对路径 |
| `utc_now_iso()` | UTC ISO 8601 时间戳字符串 |
| `safe_name(name, fallback)` | 文件名净化（去除路径分隔符与非法字符） |

> dry_run 判定不在此处：统一走基类 `Plugin.is_dry_run(ctx, params)`（见第 2 节）。

### dry_run 判定示例（基类 is_dry_run）

对应文件 `plugins/zhihu_digest/backend.py`：

```python
class ZhihuDigestPlugin(Plugin):
    ...
    dry_run_env = "AUTOFLOW_ZHIHU_DRY_RUN"

    def _fetch_answer(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        ...
        if self.is_dry_run(ctx, params):
            # 模拟路径：不发起真实请求，返回示例数据
            rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", "示例文本")
            return {"answer_text_path": rel, "dry_run": True}
        # 真实路径
        ...
```

判定优先级：`params` 中的 `dry_run` → `ctx.vars` 中的 `dry_run` → 插件专属环境变量（约定命名 `AUTOFLOW_<插件>_DRY_RUN`，通过类属性 `dry_run_env` 声明）。

### 安全路径读写示例

对应文件 `plugins/ai_deepseek/backend.py`：

```python
from plugins.common.helpers import read_text, write_text

# 写入产物目录，返回相对路径
summary_rel = write_text(ctx, "ai/summary.md", result.content)

# 读取产物/输入文件（防穿越校验）
input_text = read_text(ctx, str(raw_input["answer_text_path"]))
```

## 6. 配置与 Secrets(config.yaml)

`config.yaml` 位于插件目录下，结构如下（参考 `plugins/zhihu_digest/config.yaml`）：

```yaml
defaults:
  timeout_seconds: 30
  mode: auto
  dry_run: false

secrets:
  cookie_env: ZHIHU_COOKIE
  cookie_file: ZHIHU_COOKIE_FILE
```

- **`defaults`**：基类在 `__init__` 中归一为实例属性 `self.defaults`。
- **`secrets`**：每个值是一个环境变量名，loader 加载时解析为对应的环境变量值（不存在则为 `None`）传入 `config["secrets"]`；基类归一为实例属性 `self.secrets`。
- 插件直接使用 `self.defaults` / `self.secrets`，或通过基类 `setting(params, key, env_var=..., default=...)` 走统一取值链。
- 无 `config.yaml` 时 loader 传入 `config=None`（此时 `self.defaults` / `self.secrets` 为空字典）。

参考 `plugins/openclaw/backend.py`：OpenClaw 插件在 `__init__` 中经 `super().__init__(config)` 归一配置，handler 为实例方法直接读取 `self.defaults` / `self.secrets`。

## 7. 注册表与插件加载

### plugins.yaml

在 `plugins/plugins.yaml` 中控制插件启用状态：

```yaml
plugins:
  zhihu_digest:
    enabled: true
  my_plugin:
    enabled: true
    path: examples/hello_world.py   # 可选：文件插件或自定义路径
```

### 加载流程（backend/app/runtime/plugin_loader.py）

1. 读取 `plugins.yaml` 中启用的插件
2. 导入对应模块（目录插件要求包含 `__init__.py`）
3. 识别模块导出的 `PLUGIN`（Plugin 子类），实例化并注入 config
4. 调用 `plugin.register()` 完成注册

### 错误处理

单个插件加载失败不影响其他插件，错误会记录到 Registry（见 `GET /api/v1/plugins` 的 `errors` 字段）。

## 8. 现有插件示例分析

### dummy：最简单的 action

对应文件 `plugins/dummy/backend.py`（见第 1 节完整代码）。

**特点分析**：

- 最简单的插件结构
- 直接返回上下文信息
- 不需要外部依赖

### hello_world：文件插件示例

对应文件 `plugins/examples/hello_world.py`：

```python
from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class HelloWorldPlugin(Plugin):
    """示例插件：注册 core.hello action"""

    name = "hello-world"
    version = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "core.hello": self._hello,
        }
        self.checks = {}

    def _hello(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        name = params.get("name", "World")
        return {"message": f"Hello, {name} from AutoFlow!"}


PLUGIN = HelloWorldPlugin
```

**特点分析**：

- 单文件插件：无需 `__init__.py`
- 注册插件名称与版本

### desktop_checkin：多 action/check 注册

对应文件 `plugins/desktop_checkin/backend.py`。

**特点分析**：

- 注册 8 个 action 与 2 个 check
- 实现高级功能：桌面自动化
- 使用基类 `is_dry_run` / `setting` 与 `is_truthy` / `safe_name` 共享工具
- 支持模拟模式（dry_run，`dry_run_env = "AUTOFLOW_DESKTOP_DRY_RUN"`）

### zhihu_digest：外部 API 调用

对应文件 `plugins/zhihu_digest/backend.py`。

**特点分析**：

- 调用外部 API：知乎（playwright）
- 使用 `read_text` / `write_text` / `utc_now_iso` 共享工具与基类 `is_dry_run` / `setting`
- 实现数据处理和存储
- 支持模拟模式与错误处理

### openclaw：config 注入

对应文件 `plugins/openclaw/backend.py`。

**特点分析**：

- 构造经基类 `__init__` 归一 `self.defaults` / `self.secrets`，handler 为实例方法直接读取
- 注册 3 个 action 与 2 个 check
- 安全控制：safe_mode 默认开启、allowed_commands 白名单

## 9. 完整开发步骤

1. 在 `plugins/` 下创建插件目录 `my_plugin/`，包含 `__init__.py`
2. 在 `backend.py` 中定义 `class MyPlugin(Plugin)`，声明 `name` / `version`（可选 `dry_run_env`），在 `__init__` 中将 `actions` / `checks` 绑定为实例方法
3. 在 `__init__.py` 中导出 `PLUGIN = MyPlugin`
4. 在 `plugins/plugins.yaml` 中登记插件（`enabled: true`）
5. 需要配置时添加 `config.yaml`（defaults + secrets）
6. 编写测试并运行 `pytest plugins/my_plugin/tests` 与 `pytest backend/tests`
7. 用示例 Flow（`docs/examples/*.flow.yaml`）验证链路，可先配 `vars: { dry_run: true }`
