# AutoFlow 插件开发指南

本文档是 AutoFlow 插件开发的完整指南，针对团队内部开发者。通读本文档即可掌握插件开发的核心概念。

## 目录

- [1. 快速入门](#1-autoflow-插件开发快速入门)
- [2. Action 开发规范](#2-action-开发规范)
- [3. Check 开发规范](#3-check-开发规范)
- [4. 现有插件示例分析](#4-现有插件示例分析)

## 1. AutoFlow 插件开发快速入门

### 最小插件结构

所有 AutoFlow 插件都是一个目录，包含以下文件：

```
插件目录/
├── __init__.py  # 包入口
├── hooks.py     # register(registry) 注册函数
└── backend.py   # 业务逻辑
```

目录插件必须包含 `__init__.py`，并被 `backend/app/runtime/plugin_loader.py` 以 `plugins.<目录名>` 导入。

### register 注册函数的写法

每个插件必须提供 `register(registry)` 函数（唯一注册入口），接收 `app.core.registry.Registry` 并直接完成注册：

```python
from app.core.registry import Registry

def register(registry: Registry) -> None:
    registry.register_plugin(name="my-plugin", version="0.1.0")
    registry.register_action("my.action", my_action)
    registry.register_check("my.check", my_check)
```

### 如何注册 action 和 check

通过 `registry.register_action()` / `registry.register_check()` 注册，类型名规则是 `插件名.功能`，例如：`zhihu.fetch_answer`、`desktop.click`。

推荐把 `register(registry)` 放在 `hooks.py`，`backend.py` 只放业务实现。插件注册失败不影响其他插件，错误会记录到 Registry（见 `GET /api/v1/plugins` 的 errors 字段）。

## 2. Action 开发规范

### ActionHandler 接口

ActionHandler 是一个调用可调用的函数，签名如下：

```python
ActionHandler = Callable[[ActionContext, dict[str, Any]], Any]
```

其中：
- `ActionContext`: 上下文信息
- `dict[str, Any]`: 参数字典
- 返回值: 任意数据结构

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
- `input`: 上一步的输入数据
- `vars`: 全局变量，可以从中读取配置信息
- `artifacts_dir`: 存储产物的目录，一般建议在此目录下创建子目录

### 返回值格式

Action 的返回值不定义，但建议返回包含关键信息的字典：

```python
return {
    "result": True,           # 执行结果
    "data": 处理后的数据,    # 具体数据
    "message": "成功执行",     # 人可读的信息
    "duration_ms": 1000,     # 执行时间（可选）
    "dry_run": False,        # 是否为模拟模式（可选）
}
```

## 3. Check 开发规范

### CheckHandler 接口

CheckHandler 是一个调用可调用的函数，签名如下：

```python
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]
```

其中：
- `CheckContext`: 上下文信息
- `dict[str, Any]`: 检查参数
- 返回值: `True`/`False` 标识检查结果

### CheckContext 包含哪些信息

```python
@dataclass(frozen=True)
class CheckContext:
    run_id: str              # 流程 ID
    step_id: str             # 步骤 ID
    action_output: Any | None # 上一步 Action 输出
    vars: dict[str, Any]     # 变量字典
```

常用的内容包括：
- `action_output`: 上一步 Action 的返回值，可以根据这些数据进行检查
- `vars`: 全局变量

### 返回 True/False

Check 的返回值必须是布尔型：

```python
return True   # 检查通过
return False  # 检查失败
```

建议在检查失败时记录具体原因，例如异常日志或系统状态。

## 4. 现有插件示例分析

### dummy_echo：最简单的 action

对应文件 `plugins/examples/dummy_echo.py`：

```python
from app.core.registry import ActionContext, Registry

def _echo(ctx: ActionContext, params: dict[str, Any]) -> Any:
    return {
        "input": ctx.input,
        "message": params.get("message"),
        "vars": ctx.vars,
    }

def register(registry: Registry) -> None:
    registry.register_plugin(name="dummy-echo", version="0.1.0")
    registry.register_action("dummy.echo", _echo)
```

**特点分析**：
- 最简单的插件结构
- 直接返回上下文信息
- 不需要外部依赖

### hello_world：带版本信息的插件

对应文件 `plugins/examples/hello_world.py`：

```python
from app.core.registry import ActionContext, Registry

def _hello(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = params.get("name", "World")
    return {"message": f"Hello, {name} from AutoFlow!"}

def register(registry: Registry) -> None:
    registry.register_plugin(name="hello-world", version="1.0.0")
    registry.register_action("core.hello", _hello)
```

**特点分析**：
- 注册插件名称与版本
- 简单函数调用，不依赖外部依赖

### desktop_checkin：多 action 注册

`plugins/desktop_checkin/hooks.py` 注册多个 action 和 check：

```python
def register(registry: Registry) -> None:
    registry.register_plugin(name="desktop-checkin", version="0.1.0")
    registry.register_action("desktop.activate_window", activate_window)
    registry.register_action("desktop.click", click)
    registry.register_check("desktop.image_exists", image_exists)
    registry.register_check("desktop.window_title_contains", window_title_contains)
```

**特点分析**：
- 注册多个 action 和 check
- 实现高级功能：桌面自动化
- 包含安全功能：模拟模式支持（dry_run）

### zhihu_digest：外部 API 调用

`plugins/zhihu_digest/hooks.py` 注册外部 API 相关动作：

```python
def register(registry: Registry) -> None:
    registry.register_plugin(name="zhihu-digest", version="0.1.0")
    registry.register_action("zhihu.fetch_answer", fetch_answer)
    registry.register_action("zhihu.post_answer_draft", post_answer_draft)
```

**特点分析**：
- 调用外部 API：知乎
- 实现数据处理和存储
- 支持模拟模式
- 包含错误处理与返回结构化结果

## 5. 完整开发步骤

1. 在 `plugins/` 下创建插件目录 `my_plugin/`，包含 `__init__.py`
2. 在 `hooks.py` 中实现 `register(registry)`，注册插件信息与 action/check
3. 在 `backend.py`（或 hooks.py 内联）实现 handler 函数
4. 在 `plugins/plugins.yaml` 中登记插件（`enabled: true`）
5. 编写测试并运行 `pytest plugins/my_plugin/tests` 与 `pytest backend/tests`
6. 用示例 Flow（`docs/examples/*.flow.yaml`）验证链路，可先配 `vars: { dry_run: true }`
