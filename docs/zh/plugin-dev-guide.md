# AutoFlow 插件开发指南

本文档是 AutoFlow 插件开发的完整指南，针对团队内部开发者。通读本文档即可掌握插件开发的核心概念。

## 目录

- [1. 快速入门](quickstart.md)
- [2. Action 开发规范](action-spec.md)
- [3. Check 开发规范](check-spec.md)
- [4. 案例分析](examples.md)
- [5. 完整步骤](step-by-step.md)

## 1. AutoFlow 插件开发快速入门

### 最小插件结构

所有 AutoFlow 插件都是一个目录，包含以下文件：

```
插件目录/
└── __init__.py  # 核心文件，定义插件类和 register 函数
```

### register(注册)函数的写法

每个插件都必须提供 `register()` 函数，返回插件对象：

```python
类插件类名：
    def __init__(self) -> None:
        self.name = "插件名称"
        self.version = "0.1.0"
        self.actions = {
            "插件指定类型名": 处理函数,
        }
        self.checks = {
            "检查指定类型名": 检查函数,
        }

    def register() -> 插件类名：
        return 插件类名()
```

### 如何注册 action 和 check

在插件类的 `__init__` 方法中，通过定义 `actions` 和 `checks` 字典来注册功能：

```python
self.actions = {
    "插件指定类型名": 处理函数,
}

self.checks = {
    "检查指定类型名": 检查函数,
}
```

插件指定类型名的规则是：`插件名-功能指定`，例如：`zhihu.fetch_answer`、`desktop.click`。

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
    artifacts_dir: Path      # 产品目录
```

常用的内容包括：
- `input`: 上一步的输入数据
- `vars`: 全局变量，可以从中读取配置信息
- `artifacts_dir`: 存储产品的目录，一般建议在此目录下创建子目录

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

## 3. Check 开受规范

### CheckHandler 接口

CheckHandler 是一个调用可调用的函数，签名如下：

```python
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]
```

其中：
- `CheckContext`: 上下文信息
- `dict[str, Any]`: 检查参数
- 返回值: `True`/“False“标识检查结果

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

```python
class DummyEchoPlugin:
    def __init__(self) -> None:
        self.name = "dummy-echo"
        self.version = "0.1.0"
        self.actions = {
            "dummy.echo": self.echo,
        }

    def echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }

    def register() -> DummyEchoPlugin:
        return DummyEchoPlugin()
```

**特点分析**：
- 最简单的插件结构
- 直接返回上下文信息
- 不需要外部依赖

### hello_world：带版本信息的插件

```python
class HelloWorldPlugin:
    def __init__(self):
        self.name = "Hello World Plugin"
        self.version = "1.0.0"

    def execute(self, name: str = "World"):
        return f"Hello, {name} from AutoFlow!"

    def register():
        return HelloWorldPlugin()
```

**特点分析**：
- 使用 `execute` 方法而不是 `actions` 字典
- 简单的函数调用
- 不需要 ActionContext

### desktop_checkin：多 action 注册

```python
class DesktopCheckinPlugin:
    def __init__(self) -> None:
        self.name = "desktop-checkin"
        self.version = "0.1.0"
        self.actions = {
            "desktop.activate_window": self.activate_window,
            "desktop.click": self.click,
            # 更多 action...
        }
        self.checks = {
            "desktop.image_exists": self.image_exists,
            "desktop.window_title_contains": self.window_title_contains,
        }
```

**特点分析**：
- 注册多个 action 和 check
- 实现高级功能：桌面自动化
- 包含安全功能：模拟模式支持

### zhihu_digest：外部 API 调用

```python
class ZhihuDigestPlugin:
    def __init__(self) -> None:
        self.name = "zhihu-digest"
        self.version = "0.1.0"
        self.actions = {
            "zhihu.fetch_answer": self.fetch_answer,
            "zhihu.post_answer_draft": self.post_answer_draft,
        }
```

**特点分析**：
- 调用外部 API：知乎简介
- 实现数据处理和存储
- 支持模拟模式
- 包含错