# 设计:时间旅行调试（历史运行分叉 + 运行 diff）

- 日期:2026-09-18
- 状态:草案(待批准)
- 前置:MCP 桥第一期已合并（main `2a811d9`）；调试会话/回放/`RunSession.to_state/from_state` 已就绪
- 关联 OpenSpec 变更:`openspec/changes/time-travel-debug/`
- 路线图:`docs/roadmap.md` 第 3 节第 2 项

## 1. 背景与目标

现有能力：历史运行只能整体回放（重放请求生成新运行），调试会话只能从头开始。故障排查时常需要"从第 N 步之后继续跑"或"只重试失败步"，逐次重跑整条流程成本高且有副作用。

本轮目标：

1. **从任意历史运行任意步骤分叉出调试会话**：重建执行状态后继续单步/运行到底（含失败步重试），新运行记录保留分叉前的步骤与来源（lineage）；
2. **两次运行步骤级 diff**：对齐步骤，展示状态/Check/错误/输出的差异路径，供"修复前后对比"与回归确认。

**范围约束**：

- 不新增落盘格式（不每步存完整会话状态），从 `run.json` + `request.json` 重建；
- 分叉结果为**调试会话**（复用 `/debug` 页与既有端点），如需直接跑完可在调试页点"运行到底"；
- 旧运行（无 `request.json`）不可分叉，返回 404 明确提示；`run.json` 向后兼容（新增字段可选）；
- 多 worker 一致（复用 SessionStore 落盘 + flock）。

## 2. 状态重建（核心正确性）

`RunSession` 的运行时状态只有：`runtime_vars`、`step_outputs`、`current_input`、`index`、`run.steps`。按 `session.step()` 语义从已有落盘精确重建：

| 状态 | 重建规则 |
|---|---|
| `run.steps` 前缀 | `source.steps[:next_step_index]` 原样复制（含 skipped/failed） |
| `current_input` | 初始为 `request.input`；对每个 **success** 步：`= step.action_output`；skipped/failed 不变 |
| `step_outputs` | 对每个 **success** 且 `action_output != None` 的步：`step_outputs[step_id] = action_output`（与 `run.steps` 中一致，含外置后的 `__artifact__`） |
| `runtime_vars` | 初始为 `request.vars`；对每个 **success** 步且 `step_spec.output_var` 非空：赋值 `to_jsonable(action_output)` |

- 逐条对齐 `flow.steps[i]` ↔ `source.steps[i]`（每执行一步恰好追加一条结果，skipped 也追加）；
- `failed` 步只可能出现在前缀末尾（运行在失败处终止），其规则与 session 一致：不更新 `current_input`；
- **分叉点语义** `next_step_index`（0-based，下一个要执行的步骤下标）：
  - `k` = 重试第 k 步（失败步重试用）
  - `k+1` = 从第 k 步之后继续（跳过该步）
  - 校验 `0 ≤ next_step_index ≤ min(len(source.steps), len(flow.steps))`，否则 400。

**Lineage**：`RunResult` 新增可选字段 `parent_run_id`、`fork_step_index`（旧 `run.json` 反序列化为 `None`，写入时随运行落盘）；新运行 `started_at` 为分叉时刻，前缀步骤保留原时间戳。

## 3. 后端 API

### 3.1 分叉调试会话

`POST /api/v1/debug/sessions/fork`

```json
{ "run_id": "<历史 run>", "next_step_index": 2 }
```

- 加载 source run（404）与 `request.json`（404 `run has no stored request`）；解析 `flow_yaml`（400）
- 校验下标（400）；`RunSession.fork_from_run(...)` 重建并落盘新 run + request + 会话状态
- 返回既有 `DebugSessionSnapshot`，新增字段 `parent_run_id`/`fork_step_index`（可选）
- 新会话 id = 新 run_id；后续 `step`/`run`/`delete` 端点完全复用

### 3.2 运行 diff

`GET /api/v1/runs/{base_id}/diff/{target_id}` → `RunDiff`

- `summary`：两边的 run_id/flow_name/status/started_at/duration_ms
- `steps`：按 `(step_id, 出现序号)` 对齐（保留 base 顺序，再补 target 独有），每项含：
  - `base_index`/`target_index`（可能为 null）、`base_status`/`target_status`
  - `check_changed` + 两边 `check_passed`、`base_error`/`target_error`
  - `output_changed` + `output_diff`（叶子级差异 `{path, base, target}`，上限 100 条）
- 深层 diff 工具 `app/runtime/utils/diff.py::deep_diff`，标量/长度/新增键/类型变化均产出条目

## 4. 前端

- **运行历史（`RunsView`）**
  - 每步 "分叉" 下拉：`重试该步`（next=k）/ `从下一步继续`（next=k+1）；调用分叉 API 后跳转 `/debug?session=<id>`；
  - 运行中/无请求的运行禁用分叉并提示；
  - 表格行多选（恰选 2 条）→ "对比"：打开 `RunDiffPanel` 弹窗（状态/检查/错误差异、输出差异路径列表）
- **结果面板（`ResultsPanel`）**：新增可选 `forkable` 开关与 `fork` 事件（仅 RunsView 传入），步骤折叠头内渲染分叉下拉；顶部展示 `分叉自 <run>`（若 lineage 存在）
- **调试页（`DebugView`）**：恢复分叉会话时展示来源标签（快照新增字段）

## 5. 测试与验证

**单测**

1. `test_fork.py`
   - 重建正确性：含 `output_var`、`{{steps.X.output}}`、`{{vars.x}}` 的流程跑完后，从 index 2 分叉继续，后续输出与原运行一致；
   - 失败步重试：`next_step_index` = 失败步下标，重试成功；`k+1` 跳过失败步；
   - lineage 字段、request 落盘（可回放）、`next_step_index=0`、越界 400、无请求 404、旧 run.json 兼容；
2. `test_diff.py`：`deep_diff` 单元（标量/嵌套/列表长度/新增键/截断）；API 对齐（同 flow 两次不同 vars，状态与输出差异、目标独有步骤）。

**回归（run-checks 新增）**

- check 16 分叉：执行 → 分叉（重试成功步）→ 单步 → 运行到底 → 断言 lineage、前缀步骤、最终状态；
- check 17 diff：两次执行同流程不同输入 → diff 返回 output_changed 与差异路径。

预期：pytest ≥ 185、回归 ≥ 82。

## 6. 文档

- `docs/zh/modules/runner.md`：新增"分叉（时间旅行）"与"运行 diff"小节；
- `docs/zh/frontend/overview.md`：历史页新增对比/分叉入口说明；
- `docs/roadmap.md`：第 3 节时间旅行调试标记交付（合并后）。

## 7. 明确不做

- 不保存每步完整会话快照（本轮用重建方案）；
- 不做实时"边跑边对比"或 GUI 三窗 diff；
- 不做跨 Flow 语义对齐（不同 Flow 按 step_id 对齐，展示差异即可）；
- 不做自动修复/自动重试策略。
