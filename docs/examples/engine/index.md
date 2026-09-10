---
title: 引擎功能示例
description: 逐项验证 Flow 引擎功能的可执行示例（已通过本地实测）
keywords: [示例, engine, flow, 功能验证]
version: "1.0"
---

# 引擎功能示例

每个文件对应一项引擎功能，均可直接通过 `POST /api/v1/runs/execute` 执行。

## 文件列表

- [01_basic_actions](01_basic_actions.flow.yaml): 内置 Action 串联 + output_var
- [02_templates](02_templates.flow.yaml): input / vars / steps 模板属性链
- [03_condition](03_condition.flow.yaml): 条件执行与 skipped 记录
- [04_foreach](04_foreach.flow.yaml): for_each 循环与 iterations
- [05_retry](05_retry.flow.yaml): 重试与退避（首次失败、重试成功）
- [06_check_failure](06_check_failure.flow.yaml): Check 失败中断流程
- [07_hooks_success](07_hooks_success.flow.yaml): on_success 钩子
- [08_hooks_failure](08_hooks_failure.flow.yaml): on_failure 钩子
- [09_large_output](09_large_output.flow.yaml): 大输出外置为 artifact
- [10_plugins_dry_run](10_plugins_dry_run.flow.yaml): 插件 dry_run 覆盖
- [11_openclaw_local](11_openclaw_local.flow.yaml): OpenClaw 本地闭环与优雅报错
