---
title: 设计草案 Flow
description: 尚未实现能力的 OpenClaw 草案示例
keywords: [drafts, 草案, openclaw, flow]
version: "1.0"
---

# 设计草案 Flow

这些示例表达目标形态与编排思路，**当前引擎不可运行**，仅作设计参考。

## 文件列表

- [openclaw_code_review](openclaw_code_review.flow.yaml): 代码审查流水线（PR diff → lint → 多 Agent 审查 → 评论）
- [openclaw_daily_report](openclaw_daily_report.flow.yaml): 每日晨会报告（收集 Agent 状态 → 汇总 → 记录 KnowFlow）
- [openclaw_project_init](openclaw_project_init.flow.yaml): 项目初始化（目录结构 → OpenSpec → Git 分支 → 记录）
- [openclaw_security_audit](openclaw_security_audit.flow.yaml): 定期安全审计（端口/配置/依赖/敏感信息 → 报告）
- [openclaw_skill_update](openclaw_skill_update.flow.yaml): 技能市场批量更新（检查 → 审查 → 更新）

## 与当前实现的差距

**模板语法**（引擎仅支持 `{{steps.X.output[.path]}}`、`{{vars.X[.path]}}`、`{{input[.path]}}`，见 [engine/02_templates](../engine/02_templates.flow.yaml)）：

- `{{secrets.x}}`：无 secrets 上下文；密钥当前通过插件配置的 `env:VAR` 或调用方 `vars` 传入
- `{{vars.x | default(...)}}`：不支持默认值过滤器；引用缺失时保留原文

**Action 类型**：`openclaw.spawn_agent`、`openclaw.send_message`、`openclaw.write_file` 未注册；当前 openclaw 提供 `openclaw.http_request`、`openclaw.exec`、`openclaw.knowflow_record`

**Check 类型**：`http.statusOk`、`text.notEmpty`、`exit_code.zero`、`json.hasField` 未注册；当前为 `openclaw.status_code_ok`、`openclaw.exit_code_zero`

能力补齐后，草案将迁回 [examples](../index.md) 并纳入 API 回归。
