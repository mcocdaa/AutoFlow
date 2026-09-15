# 任务清单

- [ ] Task 1: CI action 版本升级(checkout v7 / setup-python v7 / cache v6 / setup-node v7 / docker v4,v6,v7;独立 PR)
- [ ] Task 2: `HookResult` 模型 + runner 记录 + hooks 单测
- [ ] Task 3: `RunSession` 抽取(纯重构,`Runner.run_flow` 委托,既有 134 测试全绿)
- [ ] Task 4: `SessionStore`(落盘 + flock)+ 会话状态序列化 + 单测
- [ ] Task 5: Debug API(创建/查询/单步/到底/删除)+ 回归脚本 check 13
- [ ] Task 6: 请求落盘 + `POST /runs/{id}/replay` + 回归 check 14 与 07/08 hook_results 断言
- [ ] Task 7: 前端 Hooks 展示
- [ ] Task 8: 抽取 `FlowParamsEditor` 共享组件(运行页/调试页复用)
- [ ] Task 9: 前端单步调试页(含断点、停止、`?session=` 恢复)+ 路由菜单
- [ ] Task 10: 历史详情"回放"
- [ ] Task 11: 文档更新 + 全量验证(pytest/ruff/lint/build/容器 51+/Playwright)+ 归档 openspec
