# 运行可观测性与单步调试 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 hooks 执行结果进入 API/UI 可见；把执行引擎重构为可暂停的 `RunSession`，提供调试会话 API 与前端单步调试页（含前端断点）；持久化执行请求并支持历史运行回放；顺带升级 CI action 版本。

**Architecture:** 执行逻辑从 `Runner` 下沉到 `RunSession`（整条执行 = 会话跑到底），调试 API 以"会话文件 + flock 锁 + 原子写"实现多 worker 一致的单步/续跑/停止；`request.json` 随运行落盘支撑回放；前端新增 `/debug` 页与 hooks 展示，断点为纯前端语义。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / pytest；Vue 3 + ant-design-vue 4 + CodeMirror 6 + ESLint 10；Docker 单镜像（4 worker）。

**调研依据:** 设计文档 `docs/superpowers/specs/2026-09-15-runtime-debug-observability-design.md`；OpenSpec 变更 `openspec/changes/runtime-debug-observability/`。

**验证基线（实施前确认）:** `pytest` 134 passed；`ruff` 全绿；`npm run lint` / `npm run build:web` 通过；容器 `run-checks.sh` 51/51。

**分支策略:**
- PR A（Task 1）:`chore/ci-actions-bump`，独立小 PR
- PR B（Task 2-11）:`feat/runtime-debug-observability`，两个 PR 无文件冲突，谁先合都可以

---

## Task 1: CI action 版本升级（PR A）

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: 升级 ci.yml**

checkout `v5→v7`、setup-python `v6→v7`、cache `v5→v6`、setup-node `v4→v7`、setup-buildx-action `v3→v4`、build-push-action `v6→v7`（inputs 不变：`context/file/push/tags/cache-from/cache-to`）。

- [ ] **Step 2: 升级 release.yml**

checkout `v5→v7`、setup-buildx-action `v3→v4`、login-action `v3→v4`、metadata-action `v5→v6`、build-push-action `v6→v7`（inputs 不变）。

- [ ] **Step 3: 验证**

```
git push -u origin chore/ci-actions-bump
gh pr create --title "chore(ci): bump GitHub Actions to current majors"
# 等 CI：4 个 job 全绿，且不再出现 Node 20 弃用告警
```
release.yml 不在 PR 触发范围，随下次 tag 验证；输入均为跨大版本稳定项。

---

## Task 2: HookResult 模型与记录（PR B）

**Files:**
- Modify: `backend/app/runtime/models/models.py`
- Modify: `backend/app/runtime/runner/runner.py`
- Modify: `backend/tests/test_hooks.py`

- [ ] **Step 1: 模型**

新增 `HookPhase` / `HookStatus` / `HookResult`（字段见设计 3.1）；`RunResult` 增加 `hook_results: list[HookResult] = Field(default_factory=list)`。

- [ ] **Step 2: runner 记录**

`_run_hooks` 返回 `list[HookResult]`：逐条记录 `hook/action_type/started_at/finished_at/duration_ms/output/error`；失败置 `status="failed"` 并保留 `logger.warning`；输出经 `to_jsonable` + `externalize_if_large(..., file_stem=f"hook.{phase}.{i}.output")`；`run_flow` 在 hooks 后 `run.hook_results = hook_results; store.save_run(run)`。

- [ ] **Step 3: 测试**

`test_hooks.py` 增：
- `test_hook_results_recorded_on_success`（1 条，hook/action_type/status/output 正确，duration≥0）
- `test_hook_failure_recorded`（status=failed、error 含异常文本、run.status 仍 success）
- `test_hook_results_persisted`（`store.get_run(...).hook_results` 与返回一致）

- [ ] **Step 4: 验证**

```
backend/.venv/bin/python -m pytest backend/tests/test_hooks.py -q
backend/.venv/bin/python -m pytest -q
backend/.venv/bin/ruff check backend --config ruff.toml && backend/.venv/bin/ruff format --check backend --config ruff.toml
```

---

## Task 3: RunSession 抽取（纯重构）

**Files:**
- Add: `backend/app/runtime/session.py`
- Modify: `backend/app/runtime/runner/runner.py`（仅保留门面）

- [ ] **Step 1: 迁移执行逻辑**

把 `_utc_now` / `_template_context` / `_invoke_action` / `_execute_once` / `_execute_step` / `_make_step_result` / `_run_hooks` / `_finalize_run` 移入 `RunSession`；`step()` 实现原 for 循环单次迭代（condition 跳过、`_execute_step`、外置、append + save、失败 finalize 并结束、`output_var`、`current_input`）；`run_to_completion()` 循环 `step()`；最后一步后执行 hooks、置终态并落盘。

- [ ] **Step 2: 门面**

```python
class Runner:
    def __init__(self, registry, store): ...
    @property
    def artifacts_dir(self): ...
    def run_flow(self, flow, *, input=None, vars=None, request=None) -> RunResult:
        return RunSession.start(
            self._registry, self._store, flow, input=input, vars=vars, request=request
        ).run_to_completion()
```

- [ ] **Step 3: 验证（回归即重构验收）**

```
backend/.venv/bin/python -m pytest -q          # 期望 134+ passed，语义不变
backend/.venv/bin/ruff check backend --config ruff.toml
```

---

## Task 4: SessionStore（会话落盘 + 锁）

**Files:**
- Add: `backend/app/runtime/storage/session_store.py`
- Add: `backend/tests/test_session_store.py`
- Modify: `backend/app/runtime/session.py`（`to_state/from_state` 落地）

- [ ] **Step 1: 实现**

`SessionStore(artifacts_dir)`：`_sessions/<id>.json` + `<id>.lock`；`save/get/delete` 原子写；`locked(id)` 上下文管理器（`fcntl.flock`，ImportError 降级 no-op）。

- [ ] **Step 2: 会话状态序列化**

`to_state()`：`{session_id, flow, request, runtime_vars, step_outputs, current_input, index, run, hook_results}`（全部经 `to_jsonable`）；`from_state()` 反序列化重建（`FlowSpec.model_validate` / `RunResult.model_validate`）。

- [ ] **Step 3: 测试**

`test_session_store.py`：跨实例保存/读取、删除、坏文件 `get` 抛 KeyError、锁上下文可用。
`test_session.py`：start → `step()` 递增/结果累积 → 终态 success + hook_results；`from_state(to_state())` 在新 store 实例续跑得到同样结果；已结束 `step()` 幂等；失败流程 finalize failed。

- [ ] **Step 4: 验证**

```
backend/.venv/bin/python -m pytest backend/tests/test_session_store.py backend/tests/test_session.py -q
```

---

## Task 5: Debug API

**Files:**
- Add: `backend/app/api/v1/debug.py`
- Add: `backend/runtime` 快照构造（放 `session.py`：`snapshot()`）
- Modify: `tools/test/feature-checks/run-checks.py`（新增 check 13）

- [ ] **Step 1: 端点**

按设计 3.4 实现 5 个端点；快照模型 `DebugStepInfo` / `DebugSessionSnapshot`；变更端点用 `SessionStore.locked(id)` 包裹；flow 解析失败 400，会话不存在 404，已结束会话 step/run 幂等。

- [ ] **Step 2: 回归脚本 13**

`check_debug_session()`：POST 会话（内联两步 echo flow）→ 断言 `paused/0/total=2` → step ×1 → `index=1` 且 1 条结果 → `POST /run` → `status=success`、`run_id` 有值 → GET 快照一致 → DELETE 204 → 再 GET 404。注册 `_run("13", ...)`。

- [ ] **Step 3: 验证**

```
backend/.venv/bin/python -m pytest -q
# 本地起后端后：
AUTOFLOW_BASE_URL=http://localhost:3001 python3 tools/test/feature-checks/run-checks.py | tail -3
```

---

## Task 6: 请求持久化 + 回放 API

**Files:**
- Modify: `backend/app/runtime/storage/store.py`（`save_request/get_request`）
- Modify: `backend/app/runtime/session.py`（start 时落盘 request）
- Modify: `backend/app/api/v1/runs.py`（execute 传 request；新增 replay）
- Modify: `backend/tests/test_store.py`
- Modify: `tools/test/feature-checks/run-checks.py`（07/08 断言 + check 14）

- [ ] **Step 1: 存储与写入**

`RunStore.save_request(run_id, payload)`（原子写 `request.json`）/ `get_request(run_id)`（KeyError）；`RunSession.start(request=...)` 落盘；`execute_flow` 传 `request={"flow_yaml": req.flow_yaml, "input": req.input, "vars": req.vars}`。

- [ ] **Step 2: replay 端点**

`POST /api/v1/runs/{run_id}/replay`：`_require_run` → `get_request`（缺失 404 `run has no stored request`）→ 解析执行 → 返回新 RunResult（新请求同样落盘）。

- [ ] **Step 3: 测试与回归**

- `test_store.py`：request 保存/读取/删除后 404；
- `run-checks.py` 07/08 各增一条：`hook_results` 的 `hook/status` 断言；
- check 14 `check_replay()`：`09` 小 flow 执行 → `POST replay` → 新 run_id 且 `status=success`、`flow_name` 一致 → 新 run 的 `request.json` 可下载（`GET /runs/{id}/artifacts/request.json` 200）。

- [ ] **Step 4: 验证**

```
backend/.venv/bin/python -m pytest -q
```

---

## Task 7: 前端 Hooks 展示

**Files:**
- Modify: `frontend/src/types/runs.ts`（`HookResult` + `hook_results`）
- Modify: `frontend/src/components/run/ResultsPanel.vue`

- [ ] **Step 1: 类型与展示**

`HookResult` 接口（`hook/action_type/status/started_at/finished_at/duration_ms/output/error`）；`ResultsPanel` 在"步骤"后新增"Hooks"区：阶段标签（成功钩子/失败钩子）、`action_type` 等宽、状态标签、耗时、错误 alert、输出 `pre`、产物下载（把 `artifactsOf(step)` 泛化为 `artifactsOf(value)` 供 hook 复用）。

- [ ] **Step 2: 验证**

```
cd frontend && npm run lint && npm run build:web
```
用 `07_hooks_success.flow.yaml` / `08_hooks_failure.flow.yaml` 在运行页执行，确认 Hooks 区出现且状态正确。

---

## Task 8: 抽取共享 FlowParamsEditor

**Files:**
- Add: `frontend/src/components/run/FlowParamsEditor.vue`
- Modify: `frontend/src/components/run/YamlEditor.vue`

- [ ] **Step 1: 抽取**

把 input/vars 两个 JSON CodeEditor + 提示行 + JSON 校验函数抽成 `FlowParamsEditor`（props：`inputText/varsText/hint`，emits：`update:inputText/update:varsText`；暴露 `validate(): {input, vars} | null` 或由父组件持有校验函数）。`YamlEditor` 改为使用该组件，行为与文案不变。

- [ ] **Step 2: 验证**

```
cd frontend && npm run lint && npm run build:web
```
运行页回归：加载"失败重试"示例 → 参数提示显示 → 非法 JSON 仍被拦截。

---

## Task 9: 前端调试页（单步/断点/停止）

**Files:**
- Add: `frontend/src/types/debug.ts`、`frontend/src/api/debug.ts`
- Add: `frontend/src/views/DebugView.vue`
- Modify: `frontend/src/router/index.ts`、`frontend/src/App.vue`

- [ ] **Step 1: API 与类型**

`createDebugSession / fetchDebugSession / stepDebugSession / runDebugSession / deleteDebugSession`；类型对应设计 3.4 快照。

- [ ] **Step 2: 页面**

左：CodeEditor + `FlowParamsEditor` + "开始调试"；右：会话面板（状态标签、`index/total`、单步/继续（到断点）/运行到底/停止、步骤列表含 for_each/condition/retry 标记与状态、当前步骤高亮、断点开关、选中步骤详情复用结果展示逻辑）。"继续"= 循环 `step()` 至下一个断点步骤执行前或结束；停止 = DELETE + 清空；URL `?session=<id>` 支持刷新恢复。

- [ ] **Step 3: 路由与菜单**

`/debug` 路由 + 侧栏"单步调试"（`BugOutlined`，SVG）。

- [ ] **Step 4: 验证**

```
cd frontend && npm run lint && npm run build:web
```
Playwright：开始调试 → 单步两次 → 设断点 → 继续停在该步前 → 运行到底 → 停止；控制台零报错。

---

## Task 10: 历史回放入口

**Files:**
- Modify: `frontend/src/api/runs.ts`（`replayRun`）
- Modify: `frontend/src/views/RunsView.vue`

- [ ] **Step 1: 实现**

详情抽屉新增"回放"按钮：`replayRun(run_id)` → 成功 `message.success('回放完成:新 Run ID ...')` + 刷新列表 + 抽屉切换到新运行；404（旧运行无请求）→ `message.warning`。

- [ ] **Step 2: 验证**

Playwright/手工：历史 → 查看 → 回放 → 新运行出现且可查看。

---

## Task 11: 文档与全量验证

**Files:**
- Modify: `docs/zh/modules/runner.md`（调试会话/回放/hook_results）
- Modify: `docs/zh/frontend/overview.md`（单步调试与回放现状）
- Modify: `openspec/changes/runtime-debug-observability/tasks.md`（勾选）

- [ ] **Step 1: 后端全量**

```
backend/.venv/bin/python -m pytest -q
backend/.venv/bin/ruff check backend plugins tools --config ruff.toml
backend/.venv/bin/ruff format --check backend plugins tools --config ruff.toml
```

- [ ] **Step 2: 前端全量**

```
cd frontend && npm run lint && npm run build:web
```

- [ ] **Step 3: 容器回归（4 worker）**

```
bash scripts/start.sh
docker rm -f autoflow-verify
docker run -d --name autoflow-verify -p 3001:3000 -v /tmp:/tmp ghcr.io/mcocdaa/autoflow:latest
AUTOFLOW_HEALTH_URL=http://localhost:3000 ./tools/test/feature-checks/run-checks.sh http://localhost:3001   # 51+ 全过
docker rm -f autoflow-verify
docker run --rm -v /tmp:/tmp --entrypoint sh ghcr.io/mcocdaa/autoflow:latest -c "rm -f /tmp/autoflow_retry_marker /tmp/autoflow_hook_success.txt /tmp/autoflow_hook_failure.txt"
```

- [ ] **Step 4: Playwright 端到端**

覆盖：hooks 展示、调试单步/断点/到底/停止、刷新恢复（`?session=`）、历史回放、产物下载；`CONSOLE_ERRORS=[]`。

- [ ] **Step 5: 提交与 PR**

PR B 描述含：设计/计划文档链接、验证结果、已知边界（断点前端语义、会话不自动清理、release.yml 随 tag 验证）。`openspec/changes/runtime-debug-observability/tasks.md` 勾选后合入；合并后归档到 `openspec/changes/archive/2026-09-15-runtime-debug-observability/`。
