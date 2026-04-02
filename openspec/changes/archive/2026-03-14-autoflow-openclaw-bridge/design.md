# Design: AutoFlow OpenClaw Bridge

## Strategy

优先采用 **OpenClaw 技能桥接**，通过 HTTP 调用 AutoFlow API，而不是先改 AutoFlow 核心。

## Deliverables

1. `~/.openclaw/skills/autoflow/SKILL.md`
2. `~/.openclaw/skills/autoflow/scripts/`
   - `af-execute.ps1` — 执行 flow_yaml
   - `af-list.ps1` — 列出 runs
   - `af-get.ps1` — 获取 run 详情
   - `af-plugins.ps1` — 查询插件能力
3. `usage/` 文档或 SKILL.md 章节
   - 什么任务适合 AutoFlow
   - 如何把复杂流程抽象为 Flow
   - 示例模板
4. 如有必要，对 AutoFlow API 做最小修复

## Workflow Positioning

适合 AutoFlow 的场景：

- 多步且可预测的流程
- 可复用的标准操作
- 需要日志/产物/重试的流程

不适合 AutoFlow 的场景：

- 高度开放式推理
- 强依赖即时人类判断
- 单步简单命令

## Candidate Templates

1. Project bootstrap flow
2. API smoke test flow
3. Documentation sync flow
4. Code review preparation flow

## Agent Roles

- req_analyst: 梳理使用场景、模板需求、用法文档
- backend_dev: 开发桥接脚本/技能，必要时修复 API
- qa_ops: 测试脚本、验证模板、整理风险
