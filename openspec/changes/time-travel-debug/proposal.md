schema: spec-driven
created: 2026-09-18

# 时间旅行调试(2026-09-18)

## 背景

调试会话只能从头开始;历史运行只能整体回放。故障排查需要"从第 N 步之后继续"或"只重试失败步",以及修复前后的步骤级对比。

## 变更摘要

1. **历史运行分叉**:`POST /api/v1/debug/sessions/fork {run_id, next_step_index}`,按 session 语义从 `run.json + request.json` 精确重建 `runtime_vars/step_outputs/current_input/index`,生成新调试会话(可单步/运行到底);`next_step_index=k` 重试第 k 步,`k+1` 跳过。
2. **Lineage**:`RunResult` 新增可选 `parent_run_id`/`fork_step_index`(旧 run.json 兼容);新运行保留分叉前步骤副本。
3. **运行 diff**:`GET /api/v1/runs/{base}/diff/{target}`,按 `(step_id, 序号)` 对齐步骤,输出状态/Check/错误差异与输出叶子级差异路径(`deep_diff`,上限 100 条)。
4. **前端**:历史页步骤"分叉"下拉与双运行对比弹窗;结果面板分叉入口与来源标签;调试页展示分叉来源。

## 约束遵循

- 不新增每步状态落盘,重建方案与 `session.step()` 语义逐条对齐;
- REST 向后兼容:模型仅新增可选字段,旧运行分叉返回 404 明确提示;
- 多 worker 一致性沿用 SessionStore(落盘 + flock);
- 本轮不打 tag(v1.2.0 待整体验证)。

## 详细设计

见 `docs/superpowers/specs/2026-09-18-time-travel-debug-design.md`;
实施计划见 `docs/superpowers/plans/2026-09-18-time-travel-debug.md`。
