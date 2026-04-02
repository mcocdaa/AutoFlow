# Proposal: AutoFlow Global Hooks

## Why

当前 AutoFlow 与 KnowFlow 的联动存在以下问题：

1. **重复劳动**：每个 flow 都需要手动添加 `knowflow_record` 步骤才能实现执行记录归档，繁琐且容易遗漏
2. **一致性差**：不同 flow 的归档逻辑可能不一致，有的记录成功，有的忘记记录失败
3. **维护困难**：当归档逻辑需要调整时，必须逐个修改所有 flow
4. **联动薄弱**：AutoFlow 和 KnowFlow 作为核心组件，缺乏自动化的集成机制

## What Changes

### 1. Flow YAML 支持顶层 hooks 字段

修改 `backend/app/runtime/models/models.py` 中的 `FlowSpec` 模型：

- 新增 `hooks` 字段，支持 `on_success` 和 `on_failure` 两个钩子
- 钩子可以定义要执行的 action 列表

```yaml
name: example_flow
hooks:
  on_success:
    - action: knowflow_record
      params:
        type: flow_record
        status: success
  on_failure:
    - action: knowflow_record
      params:
        type: flow_record
        status: failed
steps:
  - name: step1
    action: http_request
    ...
```

### 2. Runner 自动执行钩子

修改 `runner.py`：

- 在 flow 执行成功后，自动触发 `on_success` 钩子
- 在 flow 执行失败后，自动触发 `on_failure` 钩子
- 钩子执行失败不影响主流程结果（仅记录警告日志）

### 3. 支持自动归档配置

在 `config.yaml` 中配置全局归档规则：

```yaml
autoflow:
  auto_archive:
    enabled: true
    default_hooks:
      on_success:
        - action: knowflow_record
          params:
            type: autoflow_execution
            status: success
      on_failure:
        - action: knowflow_record
          params:
            type: autoflow_execution
            status: failed
    # 可以按 flow 名称覆盖
    flow_overrides:
      sensitive_flow:
        on_success: [] # 不记录敏感 flow
```

### 4. 钩子执行上下文

- 钩子可以访问 flow 的执行结果、耗时、输入输出等上下文信息
- 支持模板变量，如 `{{ flow.name }}`、`{{ execution.duration }}`、`{{ execution.status }}`

## Scope

涉及文件：

- `backend/app/runtime/models/models.py` - `FlowSpec` 新增 `hooks` 字段
- `runner.py` - 流程结束后自动执行钩子逻辑

## Rollback Plan

1. **hooks 字段可选**：`hooks` 字段完全可选，不填则行为与现在完全一致
2. **向后兼容**：现有 flow 无需任何修改即可继续运行
3. **全局开关**：`auto_archive.enabled` 默认关闭，需要显式启用
4. **渐进式迁移**：用户可以逐步为现有 flow 添加 hooks，无需一次性全部修改

## Success Criteria

1. ✅ `FlowSpec` 模型正确解析 `hooks` 字段
2. ✅ Flow 执行成功后自动触发 `on_success` 钩子
3. ✅ Flow 执行失败后自动触发 `on_failure` 钩子
4. ✅ 全局 `auto_archive` 配置生效，未定义 hooks 的 flow 使用默认配置
5. ✅ 钩子执行失败不影响主流程执行结果
6. ✅ 模板变量在钩子参数中正确解析
7. ✅ 向后兼容：无 hooks 的现有 flow 正常运行
8. ✅ 敏感 flow 可以通过配置跳过归档
