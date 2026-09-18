---
title: Runner（执行器）
description: 执行器与调试/分叉/对比模块
keywords: [runner, session, debug, replay, fork, diff]
version: "2.1"
---

# Runner（执行器）

执行器负责把 Flow 解析为一次可追踪的执行实例（Run），驱动 Step 执行、校验、重试、产物收集与 hooks。

## 结构

- `Runner`（`backend/app/runtime/runner/runner.py`）：门面，`run_flow()` = 创建 `RunSession` 并跑到底
- `RunSession`（`backend/app/runtime/session.py`）：可暂停的执行会话，整条执行与调试单步共用同一实现
  - `step()`：执行下一个待执行步骤（condition 跳过 / for_each / retry / check 语义一致）
  - `run_to_completion()`：执行到底并触发 hooks
  - `to_state()` / `from_state()`：JSON 会话状态，支持跨 worker 恢复
  - `fork_from_run()`：从历史运行第 N 步重建状态并继续（时间旅行），见下文
  - `planned_steps()`：调试快照用的计划步骤信息

## 执行语义

- 步骤：`condition` 不满足记为 `skipped`；`for_each` 每次迭代记录 `iterations[item/output/error/check_passed/duration_ms]`
- 重试：`retry.attempts` + 指数退避；check 失败按失败处理
- 变量：`output_var` 写入运行时 vars；模板支持 `{{input}}`、`{{vars.x}}`、`{{steps.id.output}}`
- 失败即终止（后续步骤不执行），run 状态置 `failed`
- hooks：按 run 终态执行 `on_success` / `on_failure`，结果记录在 `RunResult.hook_results`（`status/output/error/duration_ms`），hook 失败不影响 run 状态

## 运行记录与产物

- 每个 run 落盘 `artifacts/<run_id>/run.json`（原子写）；执行请求落盘 `request.json`（flow_yaml/input/vars）
- 大输出（>64KB）外置为 `{"__artifact__": {path, sha256, size}}`，经 `GET /api/v1/runs/{id}/artifacts/{path}` 下载
- `RunStore` 直接读盘：多 worker 共享历史，进程重启后历史不丢

## 调试会话

- `_sessions/<session_id>.json` 落盘 + `fcntl` 文件锁，跨 worker 一致；`session_id` 即对应 run_id
- API：`POST /debug/sessions`、`GET /debug/sessions/{id}`、`POST .../step`、`POST .../run`、`DELETE .../{id}`
- 快照返回：状态（paused/success/failed）、进度、计划步骤、已执行结果、hook 结果
- 对已结束会话 `step/run` 幂等；`DELETE` 未完成的会话同时移除对应 run，已完成运行保留在历史

## 回放

- `POST /api/v1/runs/{run_id}/replay`：读取 `request.json` 重放请求生成新运行
- 旧运行（无 `request.json`）返回 404 `run has no stored request`

## 分叉（时间旅行）

- `POST /api/v1/debug/sessions/fork {run_id, next_step_index}`：从历史运行分叉出**调试会话**（可单步/继续/运行到底）
- `next_step_index = k` 表示重试第 k 步；`k+1` 表示从第 k 步之后继续（跳过）；越界 400，无 `request.json` 404
- 状态从 `run.json` 前缀 + `request.json`（input/vars）按 `session.step()` 语义重建：`current_input`/`step_outputs`/`runtime_vars`，无需额外落盘
- lineage：新 `RunResult` 记录 `parent_run_id` 与 `fork_step_index`，前缀步骤原样保留，前缀耗时不重复计时

## 运行对比（diff）

- `GET /api/v1/runs/{base_id}/diff/{target_id}`：按 `(step_id, 出现序号)` 对齐步骤，输出
  - 汇总：两边 `flow_name/status/started_at/duration_ms`
  - 步骤：`status_changed`、`check_changed`、`base_error/target_error`、`output_changed` 与 `output_diff`（叶子级 `{path, base, target}`，上限 100 条）
- 深层差异由 `app/runtime/utils/diff.py::deep_diff` 计算（字典/列表/标量/长度变化）

## 相关文档

- 运行可观测性与单步调试设计：`docs/superpowers/specs/2026-09-15-runtime-debug-observability-design.md`
- 时间旅行调试设计：`docs/superpowers/specs/2026-09-18-time-travel-debug-design.md`
- API 回归脚本：`tools/test/feature-checks/run-checks.py`（check 01-17）
