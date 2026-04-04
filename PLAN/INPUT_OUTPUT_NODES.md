# Input / Output 节点设计规范

## 一、背景与目标

DAG 工作流中，执行是**消息驱动**的：节点仅在所有必填输入端口都有消息时才执行。开始节点默认发出一个空的成功消息，驱动整个流程。

需要支持两类特殊节点：
- **InputNode（输入节点）**：暂停流程并等待外部数据注入，注入后继续执行。
- **OutputNode（输出节点）**：将数据发送到外部系统（终端、Webhook、文件等）。

---

## 二、DAG 结构约束

| 约束 | 说明 |
|------|------|
| Start 节点 | 有且仅有 **1** 个，无输入端口，输出由用户自定义 |
| End 节点 | 有且仅有 **1** 个，当其被触发时结束整个任务（所有未完成节点标记 SKIPPED） |
| Input 节点 | 可以有 **0 或多个**，每个独立等待外部输入 |
| Output 节点 | 可以有 **0 或多个**，每个独立向外部发送数据 |

---

## 三、InputNode 规范

### 3.1 端口定义

```
inputs:  []          （无必填输入；可连接可选的上游触发端口）
outputs: [{ id: "output", name: "Output", type: "any" }]
error_port: { id: "error", name: "Error", type: "any" }
```

### 3.2 配置（config）

```yaml
mode: "api"          # 当前支持 "api"；预留 "webhook" | "form" | "watch"
schema: {}           # 可选：输入数据的 JSON Schema 校验
timeout_seconds: 0   # 0 = 永久等待；>0 = 超时后走 error_port
```

### 3.3 执行语义

1. 运行器到达 InputNode 时，检查 `state.available_inputs["{node_id}.__ext__"]` 是否存在。
2. **不存在** → 序列化当前执行状态到 DB，将 `run.status` 设为 `PAUSED`，运行器返回 `{"status": "waiting", "waiting_node_id": node_id}`。
3. **存在** → 读取该值，从 `output` 端口发出，继续执行。

### 3.4 API 模式（api）

外部通过以下端点提交输入：

```
POST /api/v2/runs/{run_id}/nodes/{node_id}/input
Content-Type: application/json

{
  "data": <any>
}
```

响应：更新后的 `V2RunResponse`，若还有后续 InputNode 则 `status=paused`，否则 `status=completed/failed`。

### 3.5 其他模式（预留）

| 模式 | 触发方式 |
|------|---------|
| `webhook` | 运行器注册一个临时 Webhook URL，外部 HTTP POST 到该 URL 触发 |
| `form` | 前端展示表单，用户填写后提交 |
| `watch` | 监听文件、消息队列或外部事件，自动触发 |

---

## 四、OutputNode 规范

### 4.1 端口定义

```
inputs:  [{ id: "input", name: "Input", type: "any", required: true }]
outputs: []
error_port: { id: "error", name: "Error", type: "any" }
```

### 4.2 配置（config）

```yaml
mode: "terminal"     # 默认；预留 "webhook" | "file" | "stream" | "return"
format: "json"       # "json" | "text" | "yaml"
# webhook 模式：
url: ""
method: "POST"
headers: {}
# file 模式：
path: ""
append: false
```

### 4.3 执行语义

- **terminal（默认）**：将 `input` 的值格式化后输出到标准日志（loguru）。
- **webhook**：HTTP POST 到配置的 URL。
- **file**：写入本地文件。
- **stream**：通过 WebSocket 实时推送到前端。
- **return**：将值加入工作流最终输出。

---

## 五、执行状态扩展

### WorkflowStatus

```python
class WorkflowStatus(str, Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    WAITING   = "waiting"     # 新增：等待 InputNode 输入
    COMPLETED = "completed"
    FAILED    = "failed"
    STOPPED   = "stopped"
```

### NodeStatus

```python
class NodeStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    WAITING   = "waiting"     # 新增：InputNode 等待输入
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"
```

---

## 六、数据库模型扩展

`RunSpec` 新增列：
```python
execution_state = Column(JSON, nullable=True)
# 存储格式：
# {
#   "available_inputs": {"node_id.port_id": <value>},
#   "history": {
#     "node_id": {
#       "status": "completed",
#       "inputs": {...},
#       "outputs": {...},
#       "retry_count": 0
#     }
#   },
#   "waiting_node_id": "input_node_id"
# }
```

---

## 七、API 变更

### 现有端点修复

`POST /api/v2/workflows/{workflow_id}/runs` — 实际执行工作流（当前为空桩），返回：

```json
{
  "run_id": "...",
  "status": "paused",
  "waiting_node_id": "input_1"   // 仅当 status=paused 时存在
}
```

### 新增端点

```
POST /api/v2/runs/{run_id}/nodes/{node_id}/input
Body: { "data": <any> }
Response: V2RunResponse（含 waiting_node_id 字段）
```

---

## 八、异步 + 轮询 / 回调（预留）

节点可能需要异步执行（如调用外部 AI API、长时间任务）：

- **轮询模式**：节点发起请求后返回 `{"__async_token__": "xxx"}`，运行器检测到此 token 后将节点状态设为 WAITING；定时轮询外部接口，完成后注入结果并恢复。
- **回调模式**：节点注册临时回调 URL，外部完成后 POST 回来触发恢复。

具体实现待有实际使用场景后补充。

---

## 九、前端集成

前端收到 `status=paused` 时：
1. 在画布上高亮对应的 InputNode（标注"等待输入"）。
2. 显示输入队列面板，用户可填写数据并提交。
3. 提交后调用 `POST /runs/{run_id}/nodes/{node_id}/input`。
4. 轮询或通过 WebSocket 监听状态变化。
