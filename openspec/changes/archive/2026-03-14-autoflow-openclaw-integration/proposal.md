# AutoFlow × OpenClaw 深度融合需求提案

> 文档类型: OpenSpec Proposal
> 作者: 需求虾 (req_analyst)
> 创建时间: 2026-03-14
> 状态: Draft

---

## 1. AutoFlow 当前数据模型总结

### 1.1 核心模型结构

根据 `backend/app/runtime/models.py` 的实现，AutoFlow 当前采用以下 Pydantic 模型：

```
FlowSpec (流程定义)
├── version: str          # 版本号
├── name: str             # 流程名称
└── steps: List[StepSpec] # 步骤列表

StepSpec (步骤定义)
├── id: str               # 唯一标识（必填）
├── name: str | None      # 展示名称（可选）
├── action: ActionSpec    # 执行动作（必填）
├── check: CheckSpec      # 结果校验（可选）
└── retry: RetrySpec      # 重试策略（可选）

ActionSpec (动作定义)
├── type: str             # 动作类型（必填）
└── params: dict          # 动作参数

CheckSpec (校验定义)
├── type: str             # 校验类型（必填）
└── params: dict          # 校验参数

RetrySpec (重试策略)
├── attempts: int         # 重试次数
└── backoff_seconds: float # 退避时间

RunResult (执行结果)
├── run_id: str           # 运行ID
├── flow_name: str        # 流程名
├── status: RunStatus     # 状态 (success/failed/running)
├── steps: List[StepResult> # 各步骤结果
└── error: str | None     # 错误信息
```

### 1.2 执行语义

- **顺序执行**: Steps 按数组顺序线性执行
- **Step 原子性**: 每个 Step = Action + 可选 Check
- **失败即停**: 任一 Step 失败则整个 Flow 失败
- **无状态传递**: Step 间无内置数据流转机制

### 1.3 触发机制 (TriggerDoc)

```yaml
TriggerDoc
├── trigger:              # 触发器定义
│   ├── type: str         # 触发类型 (cron/webhook/...)
│   └── ...               # 类型特定参数
├── flow:                 # 关联流程
│   ├── ref: str          # Flow 文件路径
│   └── params: dict      # 运行参数注入
└── policy:               # 运行策略
    ├── checksEnabled: bool
    └── concurrencyKey: str
```

---

## 2. 当前模型的局限性

### 2.1 控制流缺失

| 缺失能力               | 影响场景                     | 当前 workaround                |
| ---------------------- | ---------------------------- | ------------------------------ |
| **条件分支 (if/else)** | 无法根据前置结果决定后续路径 | 拆分为多个 Flow，外部调度      |
| **循环 (for/while)**   | 无法批量处理列表数据         | 在 Action 内部实现循环，黑盒化 |
| **并行执行**           | 无法并发执行独立步骤         | 顺序执行，效率低下             |
| **错误恢复**           | 失败时无 fallback 路径       | 依赖 retry，无替代方案         |

### 2.2 变量传递缺失

```yaml
# 当前无法实现：
steps:
  - id: fetch-data
    action:
      type: http.request
    # 结果无法传递给下一步

  - id: process-data
    action:
      type: ai.summarize
      params:
        text: "{{steps.fetch-data.output}}" # ❌ 不支持
```

**影响**:

- Step 间数据隔离，无法构建数据管道
- 每个 Action 必须自包含所有输入
- 无法根据动态数据调整行为

### 2.3 上下文管理缺失

- 无全局/局部变量概念
- 无环境/配置注入机制（除 flow.params）
- 无 Step 间状态共享

### 2.4 OpenClaw 集成障碍

| 障碍                | 说明                                                           |
| ------------------- | -------------------------------------------------------------- |
| 无法 spawn Agent    | OpenClaw 的核心能力是 Agent 编排，但 AutoFlow 无此 Action 类型 |
| 无法传递 Agent 结果 | Agent 执行结果无法被后续 Step 使用                             |
| 无法条件触发 Agent  | 无法根据条件决定是否 spawn Agent                               |
| 无法批量处理        | OpenClaw 团队常需批量操作，但 AutoFlow 无循环能力              |

---

## 3. OpenClaw 与 AutoFlow 深度融合场景分析

### 3.1 场景总览

OpenClaw 团队的日常工作中有大量**可重复、可编排**的操作流程，适合注册为 AutoFlow 的 Run。

### 3.2 具体场景（5+）

#### 场景 1: 每日晨会报告自动生成

**重复操作**: 每天收集各 Agent 进度 → 汇总 → 生成报告 → 发送到飞书群

**Flow 设计**:

```yaml
name: daily-standup-report
steps:
  - id: collect-progress
    name: 收集各 Agent 进度
    action:
      type: openclaw.spawn_agent
      params:
        agent: agent_admin
        task: 收集昨日所有 Agent 任务完成情况
    check:
      type: json.hasField
      params:
        field: reports

  - id: generate-summary
    name: 生成汇总报告
    action:
      type: openclaw.spawn_agent
      params:
        agent: coord
        task: "基于以下数据生成晨会报告: {{steps.collect-progress.output}}"
    check:
      type: text.notEmpty

  - id: send-to-feishu
    name: 发送到飞书群
    action:
      type: openclaw.send_message
      params:
        channel: feishu
        target: "每日站会群"
        content: "{{steps.generate-summary.output}}"
```

---

#### 场景 2: 新成员入职自动化

**重复操作**: 新 Agent 加入 → 创建目录结构 → 初始化配置 → 发送欢迎消息

**Flow 设计**:

```yaml
name: onboarding-new-agent
steps:
  - id: create-workspace
    name: 创建工作空间
    action:
      type: fs.createDirectory
      params:
        path: "agents/{{flow.params.agent_name}}"

  - id: init-git-repo
    name: 初始化 Git 仓库
    action:
      type: shell.exec
      params:
        command: "git init && git checkout -b openclaw"
        cwd: "agents/{{flow.params.agent_name}}"

  - id: copy-templates
    name: 复制模板文件
    action:
      type: fs.copy
      params:
        source: "templates/agent/"
        dest: "agents/{{flow.params.agent_name}}/"

  - id: notify-team
    name: 通知团队
    action:
      type: openclaw.send_message
      params:
        channel: discord
        message: "🎉 欢迎 {{flow.params.agent_name}} 加入团队！"
```

---

#### 场景 3: 代码审查流水线

**重复操作**: PR 提交 → 分配审查 Agent → 收集审查意见 → 汇总反馈

**Flow 设计**:

```yaml
name: code-review-pipeline
steps:
  - id: fetch-pr-diff
    name: 获取 PR 差异
    action:
      type: github.getPRDiff
      params:
        repo: "{{flow.params.repo}}"
        pr_number: "{{flow.params.pr_number}}"

  - id: parallel-review # 需要并行支持
    name: 并行审查
    action:
      type: openclaw.spawn_agents # 多 Agent
      params:
        agents: [backend_dev, frontend_dev, qa_ops]
        task: "审查以下代码: {{steps.fetch-pr-diff.output}}"

  - id: merge-reviews
    name: 合并审查结果
    action:
      type: openclaw.spawn_agent
      params:
        agent: coord
        task: "汇总以下审查意见: {{steps.parallel-review.outputs}}"

  - id: post-comment
    name: 发布审查评论
    action:
      type: github.postComment
      params:
        content: "{{steps.merge-reviews.output}}"
```

---

#### 场景 4: 技能市场批量更新

**重复操作**: 发现技能更新 → 下载新版本 → 测试兼容性 → 批量部署

**Flow 设计**:

```yaml
name: batch-skill-update
steps:
  - id: check-updates
    name: 检查技能更新
    action:
      type: clawhub.checkUpdates
    check:
      type: json.arrayNotEmpty
      params:
        field: updates

  - id: foreach-skill # 需要循环支持
    name: 批量更新每个技能
    action:
      type: control.forEach
      params:
        items: "{{steps.check-updates.output.updates}}"
        subflow: skill-update-subflow
        itemVar: skill

  - id: generate-report
    name: 生成更新报告
    action:
      type: openclaw.spawn_agent
      params:
        agent: agent_admin
        task: "生成技能更新报告: {{steps.foreach-skill.results}}"
```

---

#### 场景 5: 安全审计定期执行

**重复操作**: 定时触发 → 运行安全扫描 → 分析结果 → 高危项自动创建 Issue

**Flow 设计**:

```yaml
name: security-audit-scheduled
steps:
  - id: run-audit
    name: 运行安全审计
    action:
      type: security_audit.run
      params:
        scope: full

  - id: check-critical # 需要条件分支
    name: 检查高危漏洞
    action:
      type: control.if
      params:
        condition: "{{steps.run-audit.output.critical_count}} > 0"
        then:
          - id: create-issues
            action:
              type: github.createIssue
              params:
                title: "🚨 发现 {{steps.run-audit.output.critical_count}} 个高危漏洞"
                body: "{{steps.run-audit.output.report}}"
          - id: alert-team
            action:
              type: openclaw.send_message
              params:
                channel: discord
                mention: "@security-team"
                message: "⚠️ 安全审计发现高危漏洞，已创建 Issue"
        else:
          - id: log-success
            action:
              type: log.info
              params:
                message: "安全审计通过，无高危漏洞"
```

---

#### 场景 6: 多 Agent 协作任务分配 (Bonus)

**重复操作**: 复杂任务 → 拆解子任务 → 分配给多个 Agent → 收集结果 → 整合输出

**Flow 设计**:

```yaml
name: multi-agent-collaboration
steps:
  - id: decompose-task
    name: 拆解任务
    action:
      type: openclaw.spawn_agent
      params:
        agent: coord
        task: "将以下任务拆解为子任务: {{flow.params.task}}"

  - id: dispatch-to-agents
    name: 分发给各 Agent
    action:
      type: openclaw.spawn_agents_map
      params:
        mapping: "{{steps.decompose-task.output.subtasks}}"
        agentSelector: "subtask.agent_type"

  - id: reduce-results
    name: 汇总结果
    action:
      type: openclaw.spawn_agent
      params:
        agent: coord
        task: "整合以下子任务结果: {{steps.dispatch-to-agents.outputs}}"
```

---

## 4. AutoFlow 后端需要增强的能力清单

### 4.1 控制流增强

#### 4.1.1 条件分支 (if/else)

```yaml
# 新增 Action 类型: control.if
action:
  type: control.if
  params:
    condition: "{{steps.prev.output.status}} == 'failed'" # 表达式语法
    then:
      - id: fallback-action
        action:
          type: http.request
          params:
            url: "{{flow.params.fallback_url}}"
    else:
      - id: continue-normal
        action:
          type: log.info
          params:
            message: "正常流程继续"
```

**实现要点**:

- 引入表达式引擎（如 Jinja2、CEL 或自定义 DSL）
- `then`/`else` 内嵌完整 Step 列表
- 支持嵌套条件

#### 4.1.2 循环 (for/while)

```yaml
# forEach 循环
action:
  type: control.forEach
  params:
    items: "{{steps.fetch-list.output.items}}"  # 列表数据源
    itemVar: "item"                              # 迭代变量名
    indexVar: "index"                            # 索引变量名（可选）
    maxIterations: 100                           # 安全限制
    steps:
      - id: process-item
        action:
          type: openclaw.spawn_agent
          params:
            task: "处理: {{item.name}}"

# while 循环
action:
  type: control.while
  params:
    condition: "{{steps.check-status.output.hasMore}} == true"
    maxIterations: 50
    steps:
      - id: fetch-page
        action:
          type: http.request
```

#### 4.1.3 并行执行

```yaml
action:
  type: control.parallel
  params:
    steps:
      - id: task-a
        action:
          type: openclaw.spawn_agent
      - id: task-b
        action:
          type: http.request
    timeoutMs: 30000
    failFast: true # 任一失败即终止全部
```

### 4.2 变量传递机制

#### 4.2.1 上下文设计

```python
# 运行时上下文结构
class ExecutionContext:
    flow_params: dict           # Flow 注入参数
    steps: dict[str, StepContext]  # 各 Step 结果
    globals: dict               # 全局变量
    locals: dict                # 当前作用域变量

class StepContext:
    status: StepStatus
    output: Any                 # Action 输出
    check_passed: bool
    duration_ms: int
```

#### 4.2.2 表达式语法

```yaml
# 变量引用语法
"{{flow.params.apiKey}}"           # Flow 参数
"{{steps.fetch-data.output}}"      # Step 输出
"{{steps.fetch-data.output.id}}"   # 嵌套字段
"{{globals.currentUser}}"          # 全局变量
"{{item.name}}"                    # 循环变量
"{{env.HOME}}"                     # 环境变量

# 表达式函数
"{{steps.list.output | length}}"   # 数组长度
"{{steps.data.output | json}}"     # JSON 序列化
"{{steps.text.output | upper}}"    # 字符串大写
```

#### 4.2.3 模型扩展

```python
# StepSpec 扩展
class StepSpec(_Base):
    id: str
    name: str | None = None
    action: ActionSpec
    check: CheckSpec | None = None
    retry: RetrySpec | None = None
    # 新增
    output_as: str | None = None    # 输出变量名
    condition: str | None = None    # 执行条件表达式
    loop: LoopSpec | None = None    # 循环配置

class LoopSpec(_Base):
    type: Literal["forEach", "while"]
    items: str | None = None        # forEach: 列表表达式
    condition: str | None = None    # while: 条件表达式
    item_var: str = "item"
    index_var: str = "index"
    max_iterations: int = 100
```

### 4.3 OpenClaw 专用 Action 类型

#### 4.3.1 openclaw.spawn_agent

```yaml
action:
  type: openclaw.spawn_agent
  params:
    agent: str | null            # Agent 名称（null 则自动选择）
    task: str                    # 任务描述
    context: dict                # 额外上下文（可选）
    timeout_ms: int              # 超时时间（默认 300000）
    priority: "normal" | "high" | "low"
    callback_url: str | null     # 完成回调（可选）
```

**输出结构**:

```json
{
  "agent_id": "agent:backend_dev:abc123",
  "status": "completed",
  "result": "Agent 执行结果文本",
  "artifacts": [{ "type": "file", "path": "/tmp/output.md" }],
  "duration_ms": 45000
}
```

#### 4.3.2 openclaw.spawn_agents (批量)

```yaml
action:
  type: openclaw.spawn_agents
  params:
    agents: ["backend_dev", "frontend_dev"]  # 并行 spawn
    task: "共同审查 PR #123"
    aggregation: "merge" | "separate"         # 结果合并方式
```

#### 4.3.3 openclaw.send_message

```yaml
action:
  type: openclaw.send_message
  params:
    channel: "discord" | "feishu" | "slack" | "webchat"
    target: str                  # 频道/群组/用户
    message: str                 # 消息内容（支持模板）
    mentions: list[str]          # @提及列表（可选）
    attachments: list[dict]      # 附件（可选）
```

#### 4.3.4 openclaw.wait_for_response

```yaml
action:
  type: openclaw.wait_for_response
  params:
    message_id: "{{steps.send_question.output.message_id}}"
    timeout_ms: 60000
    expected_patterns: ["approve", "reject"] # 可选的响应匹配
```

#### 4.3.5 openclaw.run_flow (嵌套 Flow)

```yaml
action:
  type: openclaw.run_flow
  params:
    flow_ref: "flows/sub-flow.yaml"
    params:
      input_data: "{{steps.prev.output}}"
    inherit_context: true # 是否继承父 Flow 上下文
```

---

## 5. 双向集成架构建议

### 5.1 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层 (User Layer)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ AutoFlow UI  │  │ OpenClaw Chat│  │ CLI / API           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      编排层 (Orchestration)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AutoFlow Runtime (增强版)                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Flow引擎  │  │ 变量上下文│  │ 控制流   │  │ 插件系统 │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────────┐              ┌─────────────────────────────┐
│  AutoFlow 插件层     │              │   OpenClaw 原生工具层        │
│  (plugins/openclaw/) │◄────────────►│  (autoflow tool)            │
│                     │   双向 API    │                             │
│  ┌───────────────┐  │              │  ┌───────────────────────┐  │
│  │ OpenClawPlugin│  │              │  │ autoflow.run_flow()   │  │
│  │ - spawn_agent │  │              │  │ autoflow.list_flows() │  │
│  │ - send_message│  │              │  │ autoflow.get_status() │  │
│  │ - ...         │  │              │  └───────────────────────┘  │
│  └───────────────┘  │              │                             │
└─────────────────────┘              └─────────────────────────────┘
```

### 5.2 AutoFlow 侧：OpenClaw 插件

#### 5.2.1 目录结构

```
plugins/openclaw/
├── manifest.yaml           # 插件声明
├── pyproject.toml          # Python 依赖
├── openclaw/
│   ├── __init__.py
│   ├── actions.py          # Action 实现
│   ├── checks.py           # Check 实现
│   ├── client.py           # OpenClaw API 客户端
│   └── schemas/
│       ├── spawn_agent.json
│       ├── send_message.json
│       └── ...
├── tests/
└── README.md
```

#### 5.2.2 Manifest 设计

```yaml
# plugins/openclaw/manifest.yaml
name: openclaw
version: 0.1.0
description: "OpenClaw Agent 编排集成"

capabilities:
  actions:
    - type: openclaw.spawn_agent
      schema: schemas/spawn_agent.json
    - type: openclaw.spawn_agents
      schema: schemas/spawn_agents.json
    - type: openclaw.send_message
      schema: schemas/send_message.json
    - type: openclaw.wait_for_response
      schema: schemas/wait_for_response.json
    - type: openclaw.run_flow
      schema: schemas/run_flow.json

  checks:
    - type: openclaw.agent_completed
      schema: schemas/check_agent_completed.json

permissions:
  network:
    - "http://localhost:8080" # OpenClaw Gateway
  secrets:
    - "openclaw.api_key"
    - "openclaw.gateway_token"
```

#### 5.2.3 Action 实现伪代码

```python
# plugins/openclaw/openclaw/actions.py
from app.runtime.plugin import ActionHandler, ExecutionContext

class SpawnAgentHandler(ActionHandler):
    action_type = "openclaw.spawn_agent"

    async def execute(self, params: dict, ctx: ExecutionContext) -> dict:
        client = OpenClawClient(
            api_key=ctx.secrets.get("openclaw.api_key"),
            gateway_url=ctx.config.get("openclaw.gateway_url")
        )

        # 渲染模板参数
        task = self.render_template(params["task"], ctx.variables)

        # 调用 OpenClaw API
        result = await client.spawn_agent(
            agent=params.get("agent"),
            task=task,
            timeout_ms=params.get("timeout_ms", 300000)
        )

        return {
            "agent_id": result.agent_id,
            "status": result.status,
            "result": result.output,
            "artifacts": result.artifacts,
            "duration_ms": result.duration_ms
        }
```

### 5.3 OpenClaw 侧：AutoFlow 原生工具

#### 5.3.1 Tool 定义

```python
# OpenClaw 侧工具实现示例
@tool
def autoflow_run_flow(
    flow_ref: str,
    params: dict = None,
    wait_for_completion: bool = True,
    timeout_seconds: int = 300
) -> dict:
    """
    运行 AutoFlow 流程

    Args:
        flow_ref: Flow 文件路径或名称
        params: 注入到 Flow 的参数
        wait_for_completion: 是否等待完成
        timeout_seconds: 超时时间

    Returns:
        RunResult 字典
    """
    runtime = AutoFlowRuntime(base_url=CONFIG["autoflow_api_url"])

    run = runtime.start_flow(
        flow_ref=flow_ref,
        params=params or {}
    )

    if wait_for_completion:
        return runtime.wait_for_completion(run.run_id, timeout_seconds)

    return {"run_id": run.run_id, "status": "started"}

@tool
def autoflow_list_flows() -> list:
    """列出所有可用的 Flow"""
    runtime = AutoFlowRuntime(...)
    return runtime.list_flows()

@tool
def autoflow_get_run_status(run_id: str) -> dict:
    """获取运行状态"""
    runtime = AutoFlowRuntime(...)
    return runtime.get_run(run_id)
```

#### 5.3.2 使用示例

```python
# OpenClaw Agent 中使用 AutoFlow
async def handle_user_request(task: str):
    # 1. 分析任务，选择合适的 Flow
    flow = await analyze_and_select_flow(task)

    # 2. 运行 Flow
    result = await autoflow_run_flow(
        flow_ref=flow.ref,
        params={"user_task": task},
        wait_for_completion=True
    )

    # 3. 根据结果决定下一步
    if result["status"] == "success":
        return f"任务完成: {result['steps'][-1]['action_output']}"
    else:
        # 失败时 spawn 专门 Agent 处理
        return await spawn_agent(
            agent="qa_ops",
            task=f"Flow 执行失败，请分析: {result['error']}"
        )
```

### 5.4 双向通信协议

#### 5.4.1 AutoFlow → OpenClaw (HTTP/WebSocket)

```yaml
# 配置示例
openclaw:
  gateway_url: "ws://localhost:8080/ws"
  api_key: "${secrets.openclaw.api_key}"

  # 回调配置（OpenClaw 通知 AutoFlow）
  webhook_url: "http://autoflow-backend:8000/webhooks/openclaw"
```

#### 5.4.2 OpenClaw → AutoFlow (HTTP API)

```yaml
# OpenClaw 配置
autoflow:
  api_url: "http://autoflow-backend:8000/api/v1"
  api_key: "${secrets.autoflow.api_key}"
```

### 5.5 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                     Kubernetes / Docker                  │
│                                                          │
│  ┌─────────────────┐      ┌─────────────────────────┐   │
│  │  AutoFlow API   │◄────►│  OpenClaw Gateway       │   │
│  │  (FastAPI)      │      │  (WebSocket/HTTP)       │   │
│  └────────┬────────┘      └───────────┬─────────────┘   │
│           │                           │                 │
│           ▼                           ▼                 │
│  ┌─────────────────┐      ┌─────────────────────────┐   │
│  │  PostgreSQL     │      │  Redis (Agent 状态)      │   │
│  │  (Flow/Run 数据)│      │                         │   │
│  └─────────────────┘      └─────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 实施建议与优先级

### 6.1 阶段划分

| 阶段        | 目标     | 关键任务                                                                                                                   | 预计周期 |
| ----------- | -------- | -------------------------------------------------------------------------------------------------------------------------- | -------- |
| **Phase 1** | MVP 集成 | 1. 实现 `openclaw.spawn_agent` Action<br>2. 基础变量传递 (`{{steps.x.output}}`)<br>3. OpenClaw 侧 `autoflow.run_flow` Tool | 2 周     |
| **Phase 2** | 控制流   | 1. `control.if` 条件分支<br>2. `control.forEach` 循环<br>3. 表达式引擎                                                     | 2 周     |
| **Phase 3** | 高级特性 | 1. `control.parallel` 并行<br>2. `openclaw.send_message` 等更多 Action<br>3. 双向事件订阅                                  | 2 周     |
| **Phase 4** | 生态完善 | 1. 可视化 Flow 编辑器<br>2. 模板市场<br>3. 监控告警                                                                        | 4 周     |

### 6.2 技术选型建议

| 组件       | 推荐方案                   | 理由                                |
| ---------- | -------------------------- | ----------------------------------- |
| 表达式引擎 | Jinja2                     | Python 生态成熟，AutoFlow 已用 YAML |
| 异步执行   | asyncio + aiohttp          | 原生支持，性能优秀                  |
| 状态存储   | PostgreSQL + Redis         | 持久化 + 高性能缓存                 |
| 事件总线   | Redis Pub/Sub 或 WebSocket | 实时通知 Agent 状态                 |
| API 协议   | REST + WebSocket           | 兼容性好，实时性强                  |

### 6.3 风险与缓解

| 风险             | 影响 | 缓解措施                  |
| ---------------- | ---- | ------------------------- |
| 表达式注入攻击   | 高   | 沙箱执行，限制可用函数    |
| 无限循环         | 中   | 强制 `maxIterations` 限制 |
| Agent 长时间阻塞 | 中   | 超时机制 + 异步回调       |
| 版本兼容性问题   | 中   | Flow 版本号 + 迁移脚本    |

---

## 7. 核心发现总结

### 7.1 AutoFlow 现状

- **优势**: 结构清晰、插件化设计、可观测性好
- **核心局限**: 无控制流、无变量传递、与 Agent 生态割裂

### 7.2 融合价值

| 维度       | 价值                                     |
| ---------- | ---------------------------------------- |
| **效率**   | 将重复人工操作自动化，减少 50%+ 协调成本 |
| **可靠性** | 标准化流程，减少人为遗漏                 |
| **可扩展** | 新场景只需编写 Flow，无需改代码          |
| **可视化** | Flow 即文档，降低团队沟通成本            |

### 7.3 关键成功因素

1. **变量传递是基石**: 没有它，Step 间无法协作
2. **控制流是灵魂**: 没有它，无法处理复杂业务逻辑
3. **双向集成是闭环**: AutoFlow 调用 OpenClaw，OpenClaw 也能编排 AutoFlow

---

## 附录

### A. 参考文档

- `backend/app/runtime/models.py` - 数据模型定义
- `backend/app/runtime/flow_loader.py` - Flow 加载器
- `docs/zh/specs/flow.md` - Flow 规范
- `docs/zh/specs/plugin-sdk.md` - 插件 SDK 规范
- `docs/zh/specs/trigger-doc.md` - TriggerDoc 规范

### B. 术语对照

| AutoFlow | OpenClaw         | 说明         |
| -------- | ---------------- | ------------ |
| Flow     | Task / Session   | 可执行流程   |
| Step     | Sub-task         | 流程中的步骤 |
| Action   | Tool Call        | 具体执行动作 |
| Check    | Validation       | 结果校验     |
| Run      | Execution        | 一次执行实例 |
| Trigger  | Event / Schedule | 触发机制     |
