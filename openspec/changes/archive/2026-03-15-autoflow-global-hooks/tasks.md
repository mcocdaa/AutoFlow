# Tasks: autoflow-global-hooks

## Task 1: 定义 HookSpec 模型

- [ ] 在 `backend/app/runtime/models/models.py` 新增 `HookSpec` 类
- [ ] `HookSpec` 包含：`on_success: list[ActionSpec] | None` 和 `on_failure: list[ActionSpec] | None`

## Task 2: 扩展 FlowSpec 模型

- [ ] `FlowSpec` 新增可选字段：`hooks: HookSpec | None = None`
- [ ] 确保向后兼容：不填 hooks 时行为与现在完全一致

## Task 3: 修改 runner.py 执行钩子

- [ ] 在流程执行结束后（success 或 failure），检查 `flow.hooks` 是否存在
- [ ] 提取 hook 执行逻辑为独立方法 `_run_hooks(hooks, context)`

## Task 4: 实现 on_success 钩子

- [ ] 流程所有步骤成功后，依次执行 `hooks.on_success` 中的 action
- [ ] 钩子执行失败不影响主流程状态（捕获异常，记录日志）
- [ ] 钩子可访问流程变量（`{{steps.xxx.output}}`、`{{vars.xxx}}`）

## Task 5: 实现 on_failure 钩子

- [ ] 流程任意步骤失败后，依次执行 `hooks.on_failure` 中的 action
- [ ] 向钩子注入 `{{error.step_id}}` 和 `{{error.message}}` 变量
- [ ] 钩子执行失败同样不影响主流程状态

## Task 6: 编写测试

- [ ] 测试：无 hooks 时行为与原来一致
- [ ] 测试：on_success 在成功时触发，失败时不触发
- [ ] 测试：on_failure 在失败时触发，成功时不触发
- [ ] 测试：hook 自身执行失败不影响主流程 status

## Task 7: 更新示例文档

- [ ] 在 `docs/examples/` 新增带 hooks 的 flow YAML 示例
- [ ] 示例展示：flow 成功后自动调用 `openclaw.knowflow_record` 归档结果
