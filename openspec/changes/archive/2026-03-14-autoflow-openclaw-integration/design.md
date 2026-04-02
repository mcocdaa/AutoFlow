# AutoFlow 与 OpenClaw 集成技术方案

> 本文档为技术分析，不涉及现有代码修改

## 一、Runner 执行流程分析

### 1.1 run_flow 方法完整流程

```
run_flow(flow: FlowSpec, input, vars) → RunResult
│
├─ 1. 初始化
│   ├─ 生成 run_id (UUID)
│   ├─ 创建 run_artifacts_dir
│   ├─ 初始化 runtime_vars = vars or {}
│   └─ current_input = input
│
├─ 2. 遍历 steps (顺序执行)
│   │
│   ├─ Step 级别的重试逻辑
│   │   attempts = step.retry.attempts
│   │   backoff = step.retry.backoff_seconds
│   │
│   └─ 尝试执行 (最多 attempts+1 次)
│       │
│       ├─ 获取 action handler
│       │   action = registry.get_action(step.action.type)
│       │
│       ├─ 执行 action
│       │   action_output = action(ActionContext, step.action.params)
│       │
│       ├─ 如果有 check
│       │   ├─ check = registry.get_check(step.check.type)
│       │   ├─ check_passed = check(CheckContext, step.check.params)
│       │   └─ 如果不通过 → 抛出 RuntimeError
│       │
│       ├─ 成功则 break 循环
│       │   失败则 sleep backoff * 2^attempt 后重试
│       │
│       └─ 记录 StepResult
│           ├─ status: success | failed
│           ├─ action_output
│           ├─ check_passed
│           └─ error (如有)
│
├─ 3. 如果任何 step 失败
│   ├─ run.status = "failed"
│   ├─ run.error = step_error
│   └─ return run (立即返回)
│
├─ 4. 步骤都成功
│   ├─ current_input = action_output (传递给下一步)
│   ├─ run.status = "success"
│   └─ return run
│
└─ 5. RunResult 包含
    run_id, flow_name, status, started_at, finished_at,
    duration_ms, steps[], error
```

### 1.2 数据流

| 阶段      | 变量                            | 用途                       |
| --------- | ------------------------------- | -------------------------- |
| 入口      | `input`, `vars`                 | 用户传入的初始输入和变量   |
| Step 1 前 | `current_input`                 | 当前 step 的输入           |
| Step 1 后 | `action_output`                 | action 执行结果            |
| Step 1 后 | `current_input = action_output` | 作为下一个 step 的输入     |
| 全局      | `runtime_vars`                  | 贯穿整个 Flow 的运行时变量 |

---

## 二、插件注册机制分析

### 2.1 Registry 注册表

```python
class Registry:
    _actions: dict[str, ActionHandler]   # type_name → handler
    _checks: dict[str, CheckHandler]     # type_name → handler
    _plugins: list[PluginInfo]           # 已加载的插件列表
    _plugin_errors: list[...]            # 加载失败的插件
```

**核心方法**：

| 方法                                  | 功能                |
| ------------------------------------- | ------------------- |
| `register_action(type_name, handler)` | 注册 action         |
| `register_check(type_name, handler)`  | 注册 check          |
| `get_action(type_name)`               | 获取 action handler |
| `get_check(type_name)`                | 获取 check handler  |
| `register_plugin(name, version)`      | 记录插件信息        |

**类型签名**：

```python
ActionHandler = Callable[[ActionContext, dict[str, Any]], Any]
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]
```

### 2.2 PluginLoader 插件加载流程

```
load_plugins_into_registry(registry)
│
├─ 确定插件目录
│   ├─ 优先: plugins_dir 参数
│   └─ 备选: _repo_root() / "plugins" + AUTOFLOW_PLUGIN_DIRS 环境变量
│
├─ 加载 examples/ 下的 .py 文件
│   ├─ module_name = "autoflow_plugins.examples.{plugin_id}"
│   ├─ 查找 register() 函数
│   └─ 调用 register() 获取 plugin_obj
│
├─ 加载顶层插件目录 (排除 examples, __pycache__)
│   ├─ 需要 __init__.py
│   ├─ module_name = "autoflow_plugins.{plugin_id}"
│   └─ 查找并调用 register()
│
└─ _register_plugin_object(plugin_obj)
    │
    ├─ 注册插件信息
    ├─ 如果有 actions dict → 逐个注册
    ├─ 如果有 checks dict → 逐个注册
    └─ 否则如果可调用 execute → 注册为 "{plugin_id}.execute"
```

### 2.3 插件结构约定

```python
# plugins/my-plugin/__init__.py

name = "my-plugin"
version = "0.1.0"

def register():
    return MyPlugin()

class MyPlugin:
    actions = {
        "my-plugin.do_something": do_something_handler,
    }
    checks = {
        "my-plugin.validate_result": validate_handler,
    }
```

---

## 三、当前 Runner 的扩展点

### 3.1 可直接扩展的位置

| 位置                 | 当前行为       | 可扩展方向                          |
| -------------------- | -------------- | ----------------------------------- |
| `run_flow` 入口      | 顺序执行 steps | **可加 if/else、for 循环**          |
| `step.action.params` | 静态字典       | **支持变量替换 `${{step.output}}`** |
| `current_input` 传递 | 线性传递       | 可改为条件分支传递                  |
| Step 失败时          | 立即返回       | 可改为继续执行或跳过                |

### 3.2 需要扩展的核心点

1. **FlowSpec.steps** → 当前是 `list[StepSpec]`，需支持条件分支
2. **变量替换** → `params` 中的 `${{step.output}}`、`${{vars.xxx}}` 需要解析
3. **控制流** → 需要 `if/else`、`for` 节点类型

---

## 四、新增 OpenClaw 插件技术方案

### 4.1 AutoFlow 侧：openclaw 插件

#### 4.1.1 目录结构

```
backend/plugins/openclaw/
├── __init__.py      # register() 函数
├── README.md        # 插件说明
└── actions/
    ├── __init__.py
    ├── spawn_agent.py
    ├── exec_command.py
    └── knowflow_record.py
```

#### 4.1.2 **init**.py 示例

```python
# plugins/openclaw/__init__.py
name = "openclaw"
version = "0.1.0"

def register():
    from .actions import spawn_agent, exec_command, knowflow_record
    return OpenClawPlugin()

class OpenClawPlugin:
    actions = {
        "openclaw.spawn_agent": spawn_agent.handle,
        "openclaw.exec_command": exec_command.handle,
        "openclaw.knowflow_record": knowflow_record.handle,
    }
```

#### 4.1.3 Action 实现示例

**spawn_agent.py**:

```python
# plugins/openclaw/actions/spawn_agent.py
from typing import Any
from app.runtime.registry import ActionContext

def handle(ctx: ActionContext, params: dict[str, Any]) -> Any:
    """
    params:
      - session_name: str
      - prompt: str
      - model: str (optional)
      - runtime: str (optional, default: auto)
    """
    # 调用 OpenClaw 的 sessions_spawn API
    # 需要通过环境变量或配置获取 OpenClaw API endpoint
    import requests
    endpoint = os.getenv("OPENCLAW_API_URL", "http://localhost:8080")
    resp = requests.post(
        f"{endpoint}/api/v1/sessions/spawn",
        json={
            "name": params["session_name"],
            "prompt": params["prompt"],
            "model": params.get("model"),
            "runtime": params.get("runtime", "auto"),
        },
    )
    return resp.json()
```

**knowflow_record.py**:

```python
# plugins/openclaw/actions/knowflow_record.py
from typing import Any
from app.runtime.registry import ActionContext

def handle(ctx: ActionContext, params: dict[str, Any]) -> Any:
    """
    params:
      - name: str
      - projectId: str
      - type: str (default: document)
      - summary: str
      - content: str
    """
    import requests
    endpoint = os.getenv("OPENCLAW_API_URL", "http://localhost:8080")
    resp = requests.post(
        f"{endpoint}/api/v1/knowflow/record",
        json={
            "name": params["name"],
            "projectId": params["projectId"],
            "type": params.get("type", "document"),
            "summary": params["summary"],
            "content": params["content"],
            "agent": "autoflow",
        },
    )
    return resp.json()
```

### 4.2 OpenClaw 侧：autoflow_run 工具

在 OpenClaw 中注册一个原生工具，让 Agent 能直接执行预定义的 Flow：

```python
# OpenClaw 插件示例 (pseudo-code)
# 注册工具: autoflow_run

def autoflow_run(flow_id: str, input: Any = None, vars: dict = None) -> RunResult:
    """
    执行一个预定义的 AutoFlow

    参数:
      flow_id: Flow 的标识符或 YAML 内容
      input: 传入 Flow 的输入数据
      vars: 运行时变量

    返回:
      RunResult (status, steps, output 等)
    """
    # 1. 解析 flow_id (如果是已知 ID，从存储加载；如果是 YAML，直接使用)
    # 2. 调用 AutoFlow API: POST /api/v1/runs/execute
    # 3. 返回执行结果
```

**使用示例 (Agent 对话)**:

```
用户: "帮我运行数据清洗流程"
Agent:
  Tool: autoflow_run(flow_id="data-cleanup", input={"raw_data": "..."})
  → 返回 RunResult
```

---

## 五、Runner 增强方案

### 5.1 变量引用 `${{step.output}}`

在 `runner.py` 中执行 action 前，对 `params` 进行预处理：

```python
def _resolve_vars(text: Any, vars: dict, steps_output: dict) -> Any:
    """递归解析 ${{...}} 变量引用"""
    if isinstance(text, str):
        # 替换 ${{vars.xxx}}
        for k, v in vars.items():
            text = text.replace(f"${{vars.{k}}}", json.dumps(v))
        # 替换 ${{step.xxx}} (前序 step 的输出)
        for step_id, output in steps_output.items():
            text = text.replace(f"${{step.{step_id}}}", json.dumps(output))
        # 尝试 parse 为 Python 对象
        try:
            return json.loads(text)
        except:
            return text
    elif isinstance(text, dict):
        return {k: _resolve_vars(v, vars, steps_output) for k, v in text.items()}
    elif isinstance(text, list):
        return [_resolve_vars(item, vars, steps_output) for item in text]
    return text
```

**调用位置**: 在 `run_flow` 中，每个 step 执行前：

```python
resolved_params = _resolve_vars(step.action.params, runtime_vars, steps_output)
action_output = action(ctx, resolved_params)
```

### 5.2 if/else 条件分支

扩展 `models.py`:

```python
class StepSpec(_Base):
    # ... 现有字段
    condition: ConditionSpec | None = None  # 新增

class ConditionSpec(_Base):
    expr: str  # 例如: "${{vars.env}} == 'prod'"
    # 或使用结构化:
    # left: str
    # op: Literal["eq", "ne", "gt", "lt", "in", "contains"]
    # right: Any
```

修改 `runner.py`:

```python
for step in flow.steps:
    # 条件判断
    if step.condition is not None:
        if not _evaluate_condition(step.condition, runtime_vars, steps_output):
            # 跳过或标记为 skipped
            run.steps.append(create_skipped_step(step))
            continue

    # 原有执行逻辑...
```

### 5.3 for 循环

扩展 `models.py`:

```python
class StepSpec(_Base):
    # ... 现有字段
    loop: LoopSpec | None = None  # 新增

class LoopSpec(_Base):
    items: str  # 例如: "${{vars.item_list}}"
    item_var: str = "item"  # 循环变量名
```

修改 `runner.py`:

```python
if step.loop is not None:
    items = _resolve_var(step.loop.items, runtime_vars, steps_output)
    for item in items:
        # 设置循环变量
        runtime_vars[step.loop.item_var] = item
        # 执行 step...
        # 收集结果到 list
```

---

## 六、总结

| 能力            | 当前状态                | 方案                            |
| --------------- | ----------------------- | ------------------------------- |
| 顺序执行 steps  | ✅ 已支持               | -                               |
| 变量传递        | ✅ `current_input` 传递 | 增强 `${{vars.xxx}}` 引用       |
| 条件分支        | ❌ 不支持               | 新增 `condition` 字段           |
| 循环            | ❌ 不支持               | 新增 `loop` 字段                |
| 调用外部服务    | ✅ Action 机制          | 新增 openclaw 插件              |
| Agent 调用 Flow | ❌ 不支持               | OpenClaw 新增 autoflow_run 工具 |

**实施优先级建议**：

1. **Phase 1**: 实现 `${{step.output}}` 变量替换（最小改动）
2. **Phase 2**: 新增 openclaw 插件（AutoFlow 调用 OpenClaw）
3. **Phase 3**: 新增 autoflow_run 工具（OpenClaw 调用 AutoFlow）
4. **Phase 4**: if/else、for 扩展（控制流增强）
