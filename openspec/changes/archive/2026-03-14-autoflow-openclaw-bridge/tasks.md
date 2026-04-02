# Tasks: AutoFlow OpenClaw Bridge

## Task 1: 需求与用法方案

- [ ] 梳理 AutoFlow 在 OpenClaw 中的使用边界
- [ ] 产出适合被封装为 Flow 的任务清单
- [ ] 产出 3-4 个 Flow 模板草案
- [ ] 产出使用说明草案
- **负责人**: req_analyst

## Task 2: 桥接技能开发

- [ ] 创建 `~/.openclaw/skills/autoflow/`
- [ ] 实现 `af-execute.ps1`
- [ ] 实现 `af-list.ps1`
- [ ] 实现 `af-get.ps1`
- [ ] 实现 `af-plugins.ps1`
- [ ] 编写 `SKILL.md`
- **负责人**: backend_dev

## Task 3: API 与模板测试

- [ ] 启动/确认 AutoFlow 服务可用
- [ ] 测试 runs execute/list/get 接口
- [ ] 测试 plugins 接口
- [ ] 测试至少一个模板 flow 可执行
- [ ] 输出测试报告与风险
- **负责人**: qa_ops

## Task 4: 集成与归档

- [ ] 审查各产出
- [ ] 修正缺陷
- [ ] git commit / push openclaw
- [ ] openspec archive
- **负责人**: coord
