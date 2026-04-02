# AutoFlow 内置能力与风险分析

> 作者: coord（代兜底虾补写）
> 日期: 2026-03-14

## 1. 内置 action/check 清单

### builtins.py 注册的 actions

| Action     | 功能     |
| ---------- | -------- |
| core.log   | 日志输出 |
| core.sleep | 延时等待 |

### builtins.py 注册的 checks

| Check            | 功能         |
| ---------------- | ------------ |
| core.always_true | 永远通过     |
| text.contains    | 文本包含检查 |

### 插件注册的 actions（通过 plugin_loader）

| 插件            | Actions                                                                          |
| --------------- | -------------------------------------------------------------------------------- |
| desktop-checkin | desktop.activate_window, desktop.click, desktop.type_text, desktop.screenshot 等 |
| zhihu-digest    | zhihu.fetch_answer, zhihu.post_answer_draft                                      |
| ai-deepseek     | ai.deepseek_summarize                                                            |
| dummy-echo      | dummy.echo                                                                       |
| hello-world     | hello_world.execute                                                              |

## 2. Store 机制

- **当前实现**: 纯内存 dict（InMemoryStore）
- **数据丢失风险**: 🔴 高 — 进程重启后所有 run 记录丢失
- **查询能力**: list_runs() 返回全部，get_run(id) 按 ID 查询
- **无持久化**: 无 SQLite/文件/数据库后端

## 3. 插件注册模式

插件需要在 `__init__.py` 中暴露 `register(registry)` 函数：

```python
def register(registry):
    registry.register_action("my.action", MyActionHandler())
    registry.register_check("my.check", MyCheckHandler())
```

## 4. 风险评估

| 风险                | 等级 | 说明                                         |
| ------------------- | ---- | -------------------------------------------- |
| 内存 store 数据丢失 | 🔴   | 重启即丢，需要后续加持久化                   |
| 插件加载失败        | 🟡   | 有 try/catch 容错，会记录错误但不阻塞启动    |
| 并发执行            | 🟡   | runner.run_flow 是同步的，多个并发请求会串行 |
| 变量注入安全        | 🟡   | 模板表达式如果不做沙箱，可能有注入风险       |

## 5. 控制流对 store/runtime 的影响

- if/else：不影响 store，只影响 runner 的 step 遍历逻辑
- for 循环：需要扩展 StepResult 以支持多次执行记录
- 变量传递：需要在 runtime_vars 中维护 step outputs 的索引

## 6. 测试策略建议

1. 每个新 action/check 必须有对应的单元测试
2. 变量传递需要端到端测试（多步 Flow，step 间引用）
3. 控制流需要边界测试（空列表 forEach、false 条件 if）
4. OpenClaw 集成需要 mock 测试（不依赖真实 OpenClaw 实例）
