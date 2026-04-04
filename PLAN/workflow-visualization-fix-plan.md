# AutoFlow 前后端全面打通 + 动态节点元数据 + 插件前端集成

## 背景与现状

前一版 UI 优化（工具栏、端口样式、YAML 编辑器、深色主题）已全部完成。

当前 AutoFlow 前后端在**运行时**严重割裂：

```
当前实际执行路径（问题路径）
=========================
[Toolbar.vue] handleExecute()
     │
     ▼
simulateExecution()  ◄── 纯前端模拟，完全不经过后端
     ├── setTimeout 假装等待 (~1s)
     ├── startNode() / completeNode() 写入 nodeStates（无真实数据）
     └── activateEdge() / completeEdge() 只改颜色

应有的执行路径（未连通）
========================
[Toolbar.vue] handleExecute()
     │
     ▼
POST /api/v2/workflows/{id}/runs  ◄── 后端 API 已存在，但从未调用
     │
     ▼
WorkflowRunner → NodeExecutor → DataRouter
     │
     ▼
WebSocket 推送 / REST 响应  ◄── 两端均已实现，从未串联
     │
     ▼
前端更新 store → 各面板渲染真实数据
```

### 关键问题汇总

| 问题 | 现状 | 影响 |
|------|------|------|
| 前端执行纯模拟 | `simulateExecution()` 不调后端 | 所有数据是假的 |
| WebSocket 未连接 | `websocket.ts` 完整但无人调用 | 无法实时推送 |
| OutputNode 字段错位 | 读 `nodes[id]`，写 `nodeStates[id]` | 永远看不到输出 |
| Start 节点无值配置 | 只能配端口名，不能配默认值 | 所有下游收到空输入 |
| core.log 读错字段 | 从 `config.message` 读，不从 `ctx.input` | Hello World 数据流断裂 |
| 节点定义硬编码 | `node-defaults.ts` + `node-templates.ts` 静态维护 | 插件新增节点必须改前端 |
| start 节点有输入端口 | 前端多定义了 input 端口 | 与后端 StartNode 不一致 |

### 架构约束

- 前后端部署在不同服务器，API 通过 `vite.config.ts` 代理（`VITE_API_PROXY_URL` / `VITE_API_URL`）
- `frontend/src/api/index.ts` 使用 `baseURL: "/api"`，跨服务器部署只需配置环境变量
- WebSocket URL 通过同一代理路由，或直接读取 `VITE_API_URL` 替换协议

---

## Phase 0（立即）：修复 start 节点端口不一致

**文件**：`frontend/src/utils/node-defaults.ts`

后端 `StartNode` 无输入端口，前端多定义了一个 input Handle，删除：

```typescript
case "start":
  return { inputs: [], outputs: [{ id: "output", name: "Output", type: "any" as const }], error_port: undefined };
```

---

## Phase 1（P0）：接通前后端执行通道

### 1.1 改造 `Toolbar.vue` handleExecute

删除 `simulateExecution()`（约 100 行）。新流程：

```typescript
const handleExecute = async () => {
  const workflowId = await workflowStore.syncToBackend();
  const startInputs = workflowStore.getStartNodeInputs();
  const { data } = await api.post(`/v2/workflows/${workflowId}/runs`, { inputs: startInputs });
  executionStore.startRun(data.run_id);
  executionStore.connectToRun(data.run_id);  // WebSocket
};
```

**降级**：后端不可用时 `try/catch` fallback 到本地模拟。

### 1.2 `dag-workflow.ts` 新增 `syncToBackend()` + `getStartNodeInputs()`

- `syncToBackend()`：导出 YAML → `POST /v2/workflows`（首次创建）或 `PUT /v2/workflows/{id}`（更新）→ 返回 `workflow_id`
- `getStartNodeInputs()`：从 start 节点的 `outputs[].default` 收集初始输入值

### 1.3 后端 `runs.py` 响应增强

`V2RunResponse` 新增字段：`node_states`, `logs`, `variables`, `edge_states`。
执行完成后从 `ExecutionState` 提取数据填充。

---

## Phase 2（P0）：修复数据断裂

### 2.1 修复 OutputNode 字段映射

**问题**：`OutputNode.vue` 读 `executionStore.nodes[id].output`，`completeNode()` 写 `executionStore.nodeStates[id]`。

**修复**：`stores/execution.ts` 的 `completeNode()` 双写 `nodes` 字段：

```typescript
function completeNode(nodeId: string, nodeName: string, result?: any) {
  updateNodeState(nodeId, { status: "completed", result });
  if (result !== undefined) {
    nodes.value[nodeId] = { ...nodes.value[nodeId], output: result };
  }
}
```

### 2.2 修复 `core.log` 动作数据接收

**文件**：`backend/app/runtime/builtins.py`

```python
async def builtin_log(ctx: ActionContext) -> dict:
    message = ctx.input.get("input") or ctx.input.get("output") or ctx.config.get("message", "")
    logger.info(f"[Log] {message}")
    return {"output": message}  # 透传给下游
```

### 2.3 Start 节点输出值配置 UI

`NodeConfigPanel.vue` start 节点配置区：为每个输出端口添加默认值输入框（JSON 格式）。

数据写入 `node.outputs[i].default` → YAML 导出包含 `default` 字段 → 后端 `StartNode.execute()` 从 `port.default` 读取（已实现，无需改动）。

### 2.4 更新 hello-world 示例

`frontend/src/constants/examples.ts` hello-world：start 节点输出端口加 `default: "Hello World"`。

---

## Phase 3（P0+P1）：WebSocket 实时推送

### 3.1 后端补全 `backend/app/api/v2/websocket.py`

`WorkflowRunner` 执行节点时通过 `websocket_manager` 广播事件：

| 事件 | 触发时机 | 数据 |
|------|---------|------|
| `node_state` | 每个节点完成后 | `{node_id, status, outputs}` |
| `run_status` | 状态变化时 | `{status}` |
| `run_paused` | InputNode 挂起时 | `{waiting_node_id}` |
| `run_completed` | 全部完成 | `{outputs, duration_ms}` |
| `run_error` | 执行失败 | `{error, node_id}` |

### 3.2 前端激活 WebSocket（`stores/execution.ts`）

```typescript
function connectToRun(runId: string) {
  const ws = createWebSocket(`/ws/runs/${runId}`);
  ws.on("node_state", (d) => updateNodeState(d.node_id, d));
  ws.on("run_paused", (d) => { pendingInputNodeId.value = d.waiting_node_id; });
  ws.on("run_completed", () => completeExecution());
  ws.on("run_error", (d) => failExecution(d.error));
  // WebSocket 断开时，降级为 3s 轮询 GET /v2/runs/{run_id}
}
```

**请求频率**：WebSocket 正常时 0 轮询；断开后 3s 轮询状态接口；详情按需拉取。

### 3.3 InputNode 内联输入（节点卡片上直接操作）

**设计**：DAG 中可能有多个 InputNode，不能弹窗。改为**节点卡片内联输入**。

- `waiting` 状态：卡片边框变琥珀色 + `@keyframes pulse-yellow` 闪烁动画
- 卡片底部展开输入区：文本框 + "提交"按钮 + 队列条数显示
- 用户直接在画布节点卡片上输入，无弹窗
- 提交调用 `POST /v2/runs/{run_id}/nodes/{node_id}/input`

**实现**：`GenericNode.vue` 末尾条件渲染 `.input-inline-zone`。

---

## Phase 4（P2）：连线数据可视化

### 4.1 后端记录边数据

`backend/app/runtime/data_router.py` `_send_to_edge()` 追加记录到 `execution_state.edge_states`。
`ExecutionState` 新增 `edge_states: Dict[str, dict] = {}` 字段。

### 4.2 前端 `CustomEdge.vue` 数据标签

连线中点叠加文字标签（hover 全 JSON，默认截断 20 字符），从 `executionStore.edgeStates[id]` 读取。

---

## Phase 5：动态节点元数据 — 后端唯一来源

**核心原则**：节点特性（端口、图标、颜色、配置 schema）**只在后端 Python 代码定义一次**。
`node-defaults.ts` 和 `node-templates.ts` 迁移完成后**删除**，不再手动维护。

### 5.1 新建 `backend/app/core/node_registry.py`

```python
@dataclass
class PortMeta:
    id: str; name: str; type: str; required: bool = False

@dataclass
class NodeMeta:
    type: str; label: str; category: str; icon: str; color: str
    inputs: list[PortMeta]; outputs: list[PortMeta]
    error_port: PortMeta | None
    config_schema: dict = field(default_factory=dict)

class NodeRegistry:
    def register(self, meta: NodeMeta): ...
    def all(self) -> list[NodeMeta]: ...
    def get(self, type: str) -> NodeMeta | None: ...

node_registry = NodeRegistry()  # 全局单例
```

### 5.2 新建 `backend/app/runtime/node_meta_defaults.py`

**一次性**定义所有内置节点元数据（start/end/input/if/switch/for/while/action/merge/split/retry 等），端口对齐 `executor.py` 和 `nodes/*.py` 实际逻辑。

这里是内置节点端口的 **canonical 定义**，取代 `node-defaults.ts`。

### 5.3 新建 `backend/app/api/v2/nodes.py`

```
GET /v2/nodes        → list[NodeMeta as dict]
GET /v2/nodes/{type} → NodeMeta as dict
```

由 `router_loader.py` 自动加载。

### 5.4 Hook `node_meta_register`（插件扩展）

`hook_manager.py` 新增 hook。`main.py` lifespan 调用顺序：

1. `register_default_nodes(node_registry)` — 内置节点
2. 插件加载
3. 触发 `node_meta_register` hook — 插件注入自定义节点

```python
# plugins/my_plugin/hooks.py
@hook_manager.hook("node_meta_register")
def register_nodes(registry: NodeRegistry):
    registry.register(NodeMeta(type="my_plugin.fetch_url", label="获取 URL", ...))
```

**效果：安装插件 → 重启后端 → 前端刷新 → 新节点自动出现，无需改前端代码。**

### 5.5 前端新建 `stores/node-meta.ts`

```typescript
export const useNodeMetaStore = defineStore("node-meta", () => {
  const metas = ref<NodeMeta[]>([]);
  const loaded = ref(false);

  async function fetchMetas() {
    if (loaded.value) return;
    metas.value = (await api.get("/v2/nodes")).data;
    loaded.value = true;
  }

  function getPortsForType(type: string) { /* 替代 getDefaultPorts() */ }
  const templates = computed(() => metas.value.map(toTemplate));

  return { metas, loaded, fetchMetas, getPortsForType, templates };
});
```

`WorkflowEditor.vue` onMounted 调用，只请求一次（Store 缓存）。

### 5.6 节点卡片内联特性栏

每类节点在画布卡片上显示 `config_schema` 中最关键的 1-2 个配置字段，动态渲染：

```
┌──────────────────────────┐
│ ⑂ if 条件判断            │  ← 头部（来自 NodeMeta）
├──────────────────────────┤
│ ○ input     true ○       │  ← 端口（来自 NodeMeta.inputs/outputs）
│             false ○      │
├──────────────────────────┤
│ condition: [___________] │  ← config_schema 动态渲染
├──────────────────────────┤
│ 等待输入: [___________]  │  ← 仅 InputNode waiting 时展开
│                  [提交]  │
└──────────────────────────┘
```

### 5.7 前端文件迁移

| 现有文件 | 处理 |
|---------|------|
| `src/utils/node-defaults.ts` | **删除** → 迁到后端 `node_meta_defaults.py` |
| `src/constants/node-templates.ts` | **删除** → 迁到后端 `NodeMeta` |
| `Canvas.vue` `NODE_TEMPLATES` / `getDefaultPorts` | 改为 `nodeMetaStore` |
| `NodePalette.vue` `NODE_TEMPLATES` | 改为 `nodeMetaStore.templates` |
| `NodeConfigPanel.vue` 硬编码配置 UI | 改为 `meta.config_schema` 动态渲染 |
| `GenericNode.vue` | 新增特性配置栏 + waiting 内联输入区 |

---

## 关键文件速查

### 后端新建/修改

| 文件 | 操作 |
|------|------|
| `backend/app/core/node_registry.py` | 新建 |
| `backend/app/runtime/node_meta_defaults.py` | 新建 |
| `backend/app/api/v2/nodes.py` | 新建 |
| `backend/app/api/v2/websocket.py` | 补全 |
| `backend/app/api/v2/runs.py` | 修改（响应增强） |
| `backend/app/runtime/models.py` | 修改（V2RunResponse 扩展） |
| `backend/app/runtime/builtins.py` | 修改（core.log 数据源） |
| `backend/app/runtime/data_router.py` | 修改（edge_states） |
| `backend/app/runtime/execution_state.py` | 修改（edge_states 字段） |
| `backend/app/main.py` | 修改（lifespan 注册 node_meta） |
| `backend/app/core/hook_manager.py` | 修改（新增 hook） |

### 前端新建/修改

| 文件 | 操作 |
|------|------|
| `frontend/src/stores/node-meta.ts` | 新建 |
| `frontend/src/stores/execution.ts` | 修改 |
| `frontend/src/stores/dag-workflow.ts` | 修改 |
| `frontend/src/components/workflow/Toolbar.vue` | 修改 |
| `frontend/src/components/workflow/NodeConfigPanel.vue` | 修改 |
| `frontend/src/components/workflow/nodes/OutputNode.vue` | 修改 |
| `frontend/src/components/workflow/nodes/GenericNode.vue` | 修改 |
| `frontend/src/components/workflow/CustomEdge.vue` | 修改 |
| `frontend/src/utils/node-defaults.ts` | 修改 → 最终删除 |
| `frontend/src/constants/examples.ts` | 修改 |

---

## 实施顺序

```
Phase 0（独立）── start 节点端口修复

Phase 1（P0）── 执行通道
  ├── dag-workflow.ts syncToBackend()
  ├── Toolbar.vue 真实执行
  └── runs.py 响应增强

Phase 2（P0）── 数据断裂修复
  ├── OutputNode 字段映射
  ├── core.log 数据源
  └── Start 节点默认值 UI

Phase 3（P1）── WebSocket 实时推送
  ├── 后端 websocket.py 补全
  └── 前端 connectToRun + InputNode 内联输入

Phase 4（P2）── 连线数据可视化

Phase 5（可并行）── 动态节点元数据
  ├── 后端 NodeRegistry + API
  └── 前端 node-meta store + 替换硬编码 + 删除旧文件
```

---

## 验证标准

```bash
# 后端
cd backend && pytest tests/ -v              # 全部通过
curl http://localhost:3001/api/v2/nodes     # 返回节点元数据 JSON

# 前端
cd frontend && npm run build                # 零 TypeScript 错误
```

**端到端验证清单**：
1. Start 节点配置面板可为输出端口设置默认值 `"Hello World"`
2. 点击"执行" → Network 面板可见 `POST /api/v2/runs` 请求
3. 画布节点状态实时变化（来自 WebSocket，非模拟延迟）
4. 执行完成后 OutputNode 显示 `"Hello World"` 输出
5. InputNode 等待时卡片琥珀色闪烁 + 底部内联输入框，直接在卡片输入不弹窗
6. 连线 hover 显示传输数据摘要
7. 安装新插件，刷新前端，新节点出现在节点库（无需改前端代码）
8. start 节点画布上无左侧 Handle（无输入端口）
