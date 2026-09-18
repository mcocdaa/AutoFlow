# 时间旅行调试 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持从任意历史运行的任意步骤分叉出调试会话（状态精确重建 + lineage），并提供两次运行步骤级 diff（API + 历史页 UI）。

**Architecture:** `RunResult` 增加可选 lineage 字段；`RunSession.fork_from_run` 按 session 语义从 `run.steps + request.json` 重建 `runtime_vars/step_outputs/current_input/index` 后创建新运行与调试会话；`POST /debug/sessions/fork` 与 `GET /runs/{id}/diff/{other}` 复用既有存储；前端在运行历史页加步骤分叉下拉与双运行对比弹窗。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / pytest；Vue 3 + ant-design-vue 4；Docker 单镜像 4 worker。

**调研依据:** `docs/superpowers/specs/2026-09-18-time-travel-debug-design.md`；OpenSpec 变更 `openspec/changes/time-travel-debug/`。

**验证基线（实施前确认）:** `pytest` 169 passed；`ruff` 全绿；容器 `run-checks.sh` 74/74。

**分支策略:** 单分支 `feat/time-travel-debug`，一个 PR；**本轮不打 tag**（v1.2.0 待下轮/整体验证后）。

---

## Task 1: 模型与序列化（lineage）

**Files:**
- Modify: `backend/app/runtime/models/models.py`
- Test: `backend/tests/test_store.py`（追加兼容性用例）

- [ ] **Step 1: 失败测试**：旧 `run.json`（无 `parent_run_id`/`fork_step_index`）可读取；新写入含 lineage 的运行往返一致。
- [ ] **Step 2: 实现**：`RunResult` 追加 `parent_run_id: str | None = None`、`fork_step_index: int | None = None`。
- [ ] **Step 3:** `pytest backend/tests/test_store.py -q` 全过。

## Task 2: 会话分叉（`RunSession.fork_from_run`）

**Files:**
- Modify: `backend/app/runtime/session.py`
- Test: `backend/tests/test_fork.py`

- [ ] **Step 1: 写失败测试**
  - 重建正确性：`vars.x` + 步输出 `output_var` + `{{steps.prev.output}}` 模板流程跑完，从 index 2 分叉继续，末步输出与原运行一致；
  - 失败步重试（`next=k`）与跳过失败步（`next=k+1`）；
  - `next=0`、越界 `ValueError`、lineage/`request.json` 落盘。
- [ ] **Step 2: 实现 `fork_from_run`**：签名

```python
@classmethod
def fork_from_run(cls, registry, store, flow, *, source_run, request, next_step_index) -> RunSession
```

按设计文档第 2 节规则重建；新 `RunResult`（新 `run_id`、`status="running"`、`steps=前缀副本`、`parent_run_id`、`fork_step_index`、`started_at=now`）；`store.save_run` + `store.save_request`。
- [ ] **Step 3:** `pytest backend/tests/test_fork.py -q` 全过。

## Task 3: 分叉 API

**Files:**
- Modify: `backend/app/api/v1/debug.py`
- Test: `backend/tests/test_api_fork.py`（TestClient）

- [ ] **Step 1: 模型扩展**：`DebugSessionSnapshot` 增加 `parent_run_id`/`fork_step_index`（默认 None）。
- [ ] **Step 2: 端点** `POST /debug/sessions/fork`（`{run_id, next_step_index}`）：404 无 run / 无请求；400 越界或 YAML 非法；成功返回快照并落会话文件（`session_id == 新 run_id`）。
- [ ] **Step 3: 测试**：成功分叉（快照 index/len(results) 正确）→ `POST .../step` → `.../run` → `GET /runs/{id}` 验证 lineage 与结果；异常分支。
- [ ] **Step 4:** `pytest backend/tests/test_api_fork.py -q` 全过。

## Task 4: diff 工具与 API

**Files:**
- Create: `backend/app/runtime/utils/diff.py`
- Modify: `backend/app/api/v1/runs.py`
- Test: `backend/tests/test_diff.py`

- [ ] **Step 1: `deep_diff` 失败测试**：标量变化、嵌套字典新增/删除键、列表长度与元素差异、超限截断。
- [ ] **Step 2: 实现 `deep_diff(base, target, *, path="$", limit=100) -> list[dict]`**。
- [ ] **Step 3: 对齐与模型**：`_align_steps` 按 `(step_id, 序号)`；新增 `RunDiff`/`StepDiff`/`RunDiffSummary` 模型与 `GET /runs/{base_id}/diff/{target_id}`（404 任一侧缺失）。
- [ ] **Step 4: 测试**：同流程两次不同 vars → `output_changed` 且路径命中；状态变化；目标独有步骤 `base_index=None`。
- [ ] **Step 5:** `pytest backend/tests/test_diff.py -q` 全过。

## Task 5: 回归脚本 check 16/17

**Files:**
- Modify: `tools/test/feature-checks/run-checks.py`

- [ ] **Step 1: check 16 分叉**：执行 `01_basic_actions` → `POST /debug/sessions/fork {next_step_index:1}` → 快照 index=1 → `step` → `run` → 断言新 run `parent_run_id`、前缀步骤、最终 success。
- [ ] **Step 2: check 17 diff**：同流程两次不同 input/vars → diff 断言 `output_changed` 步骤与 `output_diff` 非空。
- [ ] **Step 3: 本地全量回归**：venv uvicorn + `run-checks.sh http://localhost:3010`（预期 ≥82/82）。

## Task 6: 前端

**Files:**
- Modify: `frontend/src/types/runs.ts`（lineage 字段）、`frontend/src/types/debug.ts`（快照新字段）
- Modify: `frontend/src/api/runs.ts`（`fetchRunDiff`）、`frontend/src/api/debug.ts`（`forkSession`）
- Create: `frontend/src/components/run/RunDiffPanel.vue`
- Modify: `frontend/src/components/run/ResultsPanel.vue`（`forkable` + `fork` 事件 + 分叉来源标签）
- Modify: `frontend/src/views/RunsView.vue`（步骤分叉下拉、行多选对比弹窗）

- [ ] **Step 1: 类型与 API**：新增 `RunDiff`/`StepDiff`/`DiffEntry` 类型与两个 API 方法。
- [ ] **Step 2: `RunDiffPanel`**：概览（流程/状态/耗时）+ 步骤对齐表（变更高亮）+ 展开输出差异路径。
- [ ] **Step 3: `ResultsPanel`**：步骤头分叉下拉（`重试该步` / `从下一步继续`）；`run.parent_run_id` 展示。
- [ ] **Step 4: `RunsView`**：行多选（恰 2 条显示"对比"）、`fork` 事件跳转 `/debug?session=<id>`、错误提示（无请求/运行中禁用）。
- [ ] **Step 5: 构建校验**：`npm run lint` + `npm run build:web`。

## Task 7: 文档与交付

- [ ] **Step 1:** `docs/zh/modules/runner.md` 增"分叉/对比"小节；`docs/zh/frontend/overview.md` 更新历史页能力；`docs/roadmap.md` 标记时间旅行调试交付。
- [ ] **Step 2:** `pytest` 全量 + `ruff check/format`。
- [ ] **Step 3:** 重建镜像部署（3101 healthy）+ 临时容器回归 + Playwright/手工 E2E（分叉、失败重试、diff 弹窗）。
- [ ] **Step 4:** pre-commit、提交、推送 `feat/time-travel-debug`、PR、CI 4/4。
