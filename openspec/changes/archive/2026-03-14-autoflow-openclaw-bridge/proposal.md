# Proposal: AutoFlow OpenClaw Bridge

## Summary
开发 AutoFlow 的 OpenClaw 桥接件，并整理 AutoFlow 在 OpenClaw 团队中的使用方式，让复杂多步流程能够被编排为单个 Flow 执行。

## Why
当前复杂任务依然依赖多轮对话和人工串行执行，存在以下问题：
1. 重复流程（如项目初始化、测试、部署、文档归档）无法一键复用
2. 多步骤任务占用大量 token
3. 流程执行缺少统一日志与可追溯性
4. OpenClaw 虽能协调 Agent，但缺少可执行流程资产

## What Changes
1. 开发 OpenClaw 技能/脚本桥接 AutoFlow API
2. 提供 AutoFlow Flow 模板与使用说明
3. 明确哪些复杂流程适合封装为 AutoFlow
4. 如有必要，补充少量 AutoFlow 后端支持

## Scope
- ✅ OpenClaw 侧桥接技能与脚本
- ✅ AutoFlow 用法文档 / Flow 模板
- ✅ API 联调与测试
- ⚠ 少量必要的 AutoFlow 后端修复
- ❌ 大规模重构 AutoFlow 核心架构
- ❌ 立即实现 ai.decide / openclaw.event 全套扩展

## Rollback Plan
桥接件独立存在于 OpenClaw 技能目录；若 AutoFlow 后端有小改动，则通过 openclaw 分支回滚。
