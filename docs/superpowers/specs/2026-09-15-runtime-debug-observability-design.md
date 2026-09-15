# 设计:运行可观测性与单步调试（Hooks 结果可见 + 调试/回放）

- 日期:2026-09-15
- 状态:草案(待批准)
- 前置:`#27`(前端 A/B 阶段:浅色 UI、运行历史、产物下载、input/vars)已合并
- 关联 OpenSpec 变更:`openspec/changes/runtime-debug-observability/`

## 1. 背景与目标

后端已具备 Flow 执行、retry/for_each/condition/hooks、运行落盘（`run.json`）与产物下载，但存在两处"逻辑可见性"缺口：

1. **Hooks 不可见**：`_run_hooks` 只写日志，hook 的执行结果（成功/失败、输出、错误、耗时）不进入 `RunResult`，前端无法展示，用户无法确认 on_success/on_failure 是否执行、是否失败。
2. **无单步/回放**：执行只能整条 Flow 同步跑完，无法逐步执行、检查中间输出；历史运行也无法回放（请求未持久化，只有结果）。

本轮目标：
- hook 结果结构化记录并在 UI 展示；
- 提供"开始调试 → 单步/继续（到断点）/运行到底/停止"的调试会话；
- 历史运行可回放（重放保存的请求）；
- 顺带升级 CI action 版本，消除 Node 20 弃用告警。

**范围约束**：
- HTTP API 向后兼容（`RunResult` 只新增可选字段）；
- 旧的 `run.json`（无 `hook_results`、无 `request.json`）必须仍可读取，回放返回 404 并给出明确 detail；
- 多 worker 部署（容器默认 `UVICORN_WORKERS=4`）下调试会话必须跨 worker 一致；
- 不引入 Python 新依赖；前端不引入新 UI 库（图标保持 SVG）。

## 2. 现状与问题定位

| 位置 | 现状 | 问题 |
|---|---|---|
| `backend/app/runtime/runner/runner.py` `_run_hooks` | 调 action、异常只 `logger.warning` | hook 结果完全丢失 |
| `runner.run_flow` | for 循环内联执行全部步骤 | 无法暂停/续跑，无法复用为调试会话 |
| `runner._finalize_run` | 结束时 `store.save_run` | hooks 在 finalize 之后执行，hook 结果若新增字段需要二次落盘 |
| `RunResult` | 无请求信息 | 历史运行无法回放 |
| `RunStore` | run.json 落盘（上一轮改造） | 可用于会话/请求落盘，但缺少带锁的读改写与请求存取 |
| 前端 | 结果面板无 hooks；无调试页 | 能力不可见 |

## 3. 设计

### 3.1 Hook 结果模型（`models.py`）

```python
HookPhase = Literal["on_success", "on_failure"]
HookStatus = Literal["success", "failed"]


class HookResult(_Base):
    hook: HookPhase
    action_type: str
    status: HookStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    output: Any | None = None
    error: str | None = None


class RunResult(_Base):
    ...
    hook_results: list[HookResult] = Field(default_factory=list)  # 新增
```

- **不改变 run 状态语义**：hook 失败仅记录 `status="failed"` + `error`，`run.status` 不变。
- **输出外置**：hook 输出同样经过 `externalize_if_large`（`file_stem=f"hook.{phase}.{index}.output"`），与 step 输出一致。
- **落盘时机**：hooks 在 `_finalize_run` 之后执行，因此 `run.hook_results = ...` 后需再 `store.save_run(run)` 一次（仅在确有 hook 时）。
- 兼容：旧 `run.json` 无该字段 → Pydantic 默认 `[]`。

### 3.2 可暂停执行会话 `RunSession`（新 `backend/app/runtime/session.py`）

将 `Runner` 的执行逻辑下沉为会话，`Runner` 退化为薄门面，保证整条执行与单步执行**共用同一套语义**（避免双实现漂移）：

```python
class RunSession:
    @classmethod
    def start(cls, registry, store, flow, *, input=None, vars=None, request=None) -> "RunSession"
    @property
    def run(self) -> RunResult
    @property
    def finished(self) -> bool
    def step(self) -> None            # 执行下一个待执行步骤（含 condition/for_each/retry 语义）
    def run_to_completion(self) -> RunResult
    def to_state(self) -> dict        # JSON 可序列化的完整会话状态
    @classmethod
    def from_state(cls, registry, store, state) -> "RunSession"
```

- 迁移内容：`_template_context` / `_invoke_action` / `_execute_once` / `_execute_step` / `_make_step_result` / `_run_hooks` / `_finalize_run` 移入 `RunSession`；
- `Runner.run_flow(flow, input=..., vars=..., request=...)` = `RunSession.start(...).run_to_completion()`；
- 会话内部状态：`index`、`current_input`、`runtime_vars`、`step_outputs`、`run`、`hook_results`；
- 终态：`step()` 执行完最后一步后调用 finalize（含 hooks）并落盘 `run.json`；已结束会话再次 `step()` 为 no-op；
- `request` 存在时在启动阶段由 `RunStore.save_request(run_id, request)` 落盘。

**为什么不做"每步一个 HTTP 请求重建 Runner"的临时方案**：condition/for_each/retry/output_var 的状态在实例内，重建会丢语义，必须显式序列化（见 3.3）。

### 3.3 会话落盘与并发（新 `backend/app/runtime/storage/session_store.py`）

- 路径：`artifacts_dir/_sessions/<session_id>.json`（`RunStore.list_runs` 跳过无 `run.json` 的目录，互不干扰）；
- `SessionStore`：`save / get / delete`（原子替换，与 RunStore 一致）+ `locked(session_id)` 上下文管理器；
- 锁：`fcntl.flock(<id>.lock, LOCK_EX)`；非 POSIX 平台降级为无锁（本仓库后端运行于 Linux，测试亦在 Linux）；
- 所有变更端点（step / run / delete）在锁内完成"读 → 重建会话 → 执行 → 写"。

### 3.4 调试 API（新 `backend/app/api/v1/debug.py`）

| 方法 | 路径 | 语义 |
|---|---|---|
| POST | `/api/v1/debug/sessions` | `{flow_yaml, input, vars}` → 创建会话，返回快照 |
| GET | `/api/v1/debug/sessions/{id}` | 返回快照 |
| POST | `/api/v1/debug/sessions/{id}/step` | 执行一个步骤，返回快照 |
| POST | `/api/v1/debug/sessions/{id}/run` | 执行到底（含 hooks），返回快照 |
| DELETE | `/api/v1/debug/sessions/{id}` | 删除会话（204） |

快照模型：

```python
class DebugStepInfo(BaseModel):  # 计划步骤（来自 FlowSpec）
    id: str
    name: str | None
    for_each: str | None
    has_condition: bool
    retry_attempts: int
    output_var: str | None


class DebugSessionSnapshot(BaseModel):
    session_id: str
    flow_name: str
    status: Literal["paused", "success", "failed"]
    index: int  # 待执行步骤下标
    total_steps: int
    run_id: str
    steps: list[DebugStepInfo]
    results: list[StepResult]  # 已执行结果（与 run.steps 同步）
    hook_results: list[HookResult]
    error: str | None
```

错误约定：flow 解析失败 400；会话不存在 404；对已结束会话 `step/run` 幂等返回快照。

### 3.5 回放（请求持久化 + replay）

- `RunStore` 新增 `save_request(run_id, payload)` / `get_request(run_id)`（`request.json`，原子写）；
- `execute_flow` 与 `replay` 都传入 `request={"flow_yaml", "input", "vars"}`，随 run 一同落盘；
- 新增 `POST /api/v1/runs/{run_id}/replay`：读 `request.json` → 重新解析执行 → 返回新的 `RunResult`（新 run_id）；
- 旧运行无 `request.json` → 404 `detail="run has no stored request"`；
- 回放语义 = **重放当时请求**（非回看录像），结果作为新运行进入历史。

### 3.6 前端

**Hooks 展示（`ResultsPanel.vue`）**
- "步骤"之后新增"Hooks"区：每条展示 阶段标签（成功钩子/失败钩子）、`action_type`（等宽字体）、状态标签、耗时、错误 alert、输出 `pre`、产物下载（复用 `__artifact__` 识别）。

**调试页（新 `views/DebugView.vue`，路由 `/debug`，菜单"单步调试"）**
- 左：Flow YAML（CodeEditor）+ input/vars（抽出共享 `FlowParamsEditor.vue`，与运行页复用）+ "开始调试"；
- 右：会话面板
  - 头部：状态标签（调试中/成功/失败）、进度 `index/total`；
  - 操作：单步执行、继续（到断点）、运行到底、停止（DELETE）；
  - 步骤列表：计划步骤（含 for_each/condition/retry 标记）、已执行状态点、当前待执行高亮、点击查看该步详情（输出/检查/迭代/产物）；
  - 断点：**纯前端**语义（步骤 id 集合）；"继续"从当前下标逐次 `step()`，遇到下一个断点步骤**执行前**停止；后端无需 breakpoint 概念；
  - 结束后展示 hook_results（同 Hooks 展示）。
- 中断/刷新：会话在服务端落盘，刷新页面后可通过 URL 查询参数 `?session=<id>` 恢复（GET 快照）。

**回放入口（`RunsView.vue` 详情抽屉）**
- "回放"按钮 → `POST /runs/{id}/replay` → 成功提示（新 Run ID）、刷新列表、抽屉切换到新运行；404 时提示"该运行没有保存请求（旧版本运行）"。

### 3.7 CI action 版本升级（独立小改动）

`ci.yml` / `release.yml` 统一升级（CI 在 PR 上验证 `ci.yml`；`release.yml` 输入兼容，随下次 tag 验证）：

| Action | 现 | 新 |
|---|---|---|
| actions/checkout | v5 | v7 |
| actions/setup-python | v6 | v7 |
| actions/cache | v5 | v6 |
| actions/setup-node | v4 | v7 |
| docker/setup-buildx-action | v3 | v4 |
| docker/login-action | v3 | v4 |
| docker/metadata-action | v5 | v6 |
| docker/build-push-action | v6 | v7 |

## 4. 已定决策（如需调整请在批复时指出）

1. 断点语义：停在断点步骤**执行前**；继续按钮 = 执行到下一个断点前。
2. 回放语义：重放请求生成新运行，不展示旧运行的"录像"。
3. 调试会话生命周期：手动停止/删除，不做 TTL 清理（后续可加）。
4. Hook 输出：同样支持大输出外置，不分叉逻辑。
5. 调试会话同样会生成一条历史运行（完成时落 `run.json`），便于对照。

## 5. 测试与验证策略

- 单元：`test_hooks.py` 增 hook_results 断言；新增 `test_session.py`（单步/续跑/状态序列化跨实例/幂等/失败路径）；`test_store.py` 增 request.json 用例；
- API 回归（`tools/test/feature-checks/run-checks.py`）：07/08 增 `hook_results` 断言；新增 `13`（调试会话全流程）与 `14`（回放）；
- 前端：`npm run lint`、`npm run build:web`；
- 端到端（Playwright）：调试页单步/断点/运行到底/停止、hooks 展示、历史回放；控制台零报错；
- 容器：`scripts/start.sh` 重建，51+ 项回归在临时容器（4 worker + `/tmp` 挂载）通过。

## 6. 风险

| 风险 | 缓解 |
|---|---|
| `run_flow` 重构引入语义漂移 | 既有 134 单测 + 51 项 API 回归为基线；`Runner.run_flow` 仅委托，不保留旧实现 |
| 会话文件跨 worker 并发 | flock 独占 + 原子替换；step/run 幂等 |
| 会话状态含任意 output，序列化失败 | 复用 `to_jsonable`/`safe_deep_copy`；外置大输出 |
| release.yml 大版本升级未在 PR 验证 | 仅用稳定输入；tag 发布时首次验证，出问题回退单行 |
| 调试页与运行页编辑器重复 | 抽 `FlowParamsEditor` 复用；YAML 编辑器本身已为共享组件 |
