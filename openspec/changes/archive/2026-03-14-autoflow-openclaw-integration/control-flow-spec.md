# AutoFlow Phase 2 控制流增强设计规范

> 版本: 1.0
> 状态: 设计稿
> 作者: 需求虾
> 日期: 2026-03-14

## 1. 概述

本文档定义 AutoFlow Phase 2 的控制流增强功能，包括 **if/else 条件分支** 和 **for 循环** 的 YAML 语法设计，以及对现有代码的修改建议。

## 2. if/else 条件分支

### 2.1 设计目标

- 支持基于运行时变量和步骤输出的条件判断
- 条件为 false 时，step 状态标记为 `skipped`，不影响后续步骤执行
- 保持向后兼容，现有 Flow 无需修改即可运行

### 2.2 StepSpec 新增字段

```yaml
condition: str | None = None  # 条件表达式，为 None 时默认执行
```

### 2.3 条件表达式语法

条件表达式为字符串，支持以下语法：

| 语法 | 说明 | 示例 |
|------|------|------|
| `{{vars.X}}` | 引用运行时变量 | `{{vars.env}} == 'prod'` |
| `{{steps.X.output}}` | 引用步骤输出 | `{{steps.validate.output}} == true` |
| `{{input}}` | 引用当前输入 | `{{input}} != null` |
| 比较运算符 | `==`, `!=`, `<`, `>`, `<=`, `>=` | `{{vars.count}} > 5` |
| 逻辑运算符 | `and`, `or`, `not` | `{{vars.a}} == 1 and {{vars.b}} == 2` |
| 内置函数 | `empty()`, `contains()`, `len()` | `empty({{vars.list}})` |

### 2.4 YAML 示例

```yaml
version: 1
name: conditional-flow

defaults:
  timeoutMs: 30000

steps:
  - id: check-env
    name: "检查环境变量"
    action:
      type: system.getEnv
      params:
        key: "DEPLOY_ENV"
    output_var: env

  - id: prod-only-step
    name: "生产环境专属步骤"
    condition: "{{vars.env}} == 'production'"
    action:
      type: http.request
      params:
        url: "https://prod.example.com/api/notify"
        method: POST

  - id: check-user-type
    name: "获取用户类型"
    action:
      type: http.request
      params:
        url: "https://api.example.com/user/info"
    output_var: userInfo

  - id: vip-only-feature
    name: "VIP 用户专属功能"
    condition: "{{steps.check-user-type.output.level}} == 'vip'"
    action:
      type: desktop.click
      params:
        by: ocr
        text: "VIP 专区"

  - id: always-run
    name: "始终执行的步骤"
    action:
      type: system.log
      params:
        message: "流程执行完成"
```

### 2.5 执行行为

- `condition` 为 `None` 或空字符串：正常执行
- `condition` 解析结果为 `True`：正常执行
- `condition` 解析结果为 `False`：
  - step 状态设为 `skipped`
  - `started_at` 和 `finished_at` 设为当前时间
  - `duration_ms` 设为 0
  - `action_output` 设为 `None`
  - 继续执行后续步骤

## 3. for 循环

### 3.1 设计目标

- 支持对列表数据进行迭代处理
- 每次迭代作为独立的 step 执行记录
- 循环体内可访问当前元素和索引

### 3.2 StepSpec 新增字段

```yaml
for_each: str | None = None      # 引用列表变量的表达式，如 "{{vars.items}}"
for_each_as: str = "item"       # 循环变量名，默认为 "item"
for_index_as: str = "index"     # 索引变量名，默认为 "index"
```

### 3.3 循环变量引用

在配置了 `for_each` 的 step 中，以下模板变量可用：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{item}}` | 当前迭代元素（默认名） | `{{item.name}}` |
| `{{index}}` | 当前迭代索引（从 0 开始） | `{{index}}` |
| `{{forEach.item}}` | 显式访问循环变量 | `{{forEach.item.id}}` |
| `{{forEach.index}}` | 显式访问循环索引 | `{{forEach.index}}` |

### 3.4 YAML 示例

```yaml
version: 1
name: foreach-flow

defaults:
  timeoutMs: 30000

steps:
  - id: fetch-users
    name: "获取用户列表"
    action:
      type: http.request
      params:
        url: "https://api.example.com/users"
    output_var: users

  - id: process-user
    name: "处理用户"
    for_each: "{{vars.users}}"
    for_each_as: "user"
    for_index_as: "idx"
    action:
      type: http.request
      params:
        url: "https://api.example.com/users/{{user.id}}/notify"
        method: POST
        body:
          message: "Hello {{user.name}}, you are #{{idx}}"

  - id: process-files
    name: "批量处理文件"
    for_each: "{{vars.fileList}}"
    action:
      type: file.process
      params:
        path: "{{item.path}}"
        operation: "compress"
    output_var: processedFiles

  - id: summary
    name: "汇总结果"
    action:
      type: system.log
      params:
        message: "Processed {{steps.process-files.output | length}} files"
```

### 3.5 执行行为

- `for_each` 为 `None` 或空字符串：作为普通 step 执行（一次）
- `for_each` 解析结果为非列表类型：报错，step 状态为 `failed`
- `for_each` 解析为空列表：
  - step 状态设为 `skipped`
  - 记录 `skipped_reason: "empty_for_each_list"`
- `for_each` 解析为非空列表：
  - 为每个元素创建一个子 step 执行记录
  - 子 step 的 `step_id` 格式为 `{parent_id}[{index}]`，如 `process-user[0]`, `process-user[1]`
  - 所有子 step 成功，父 step 状态为 `success`
  - 任一子 step 失败，父 step 状态为 `failed`，停止后续迭代

## 4. 对 models.py 的修改建议

### 4.1 StepSpec 新增字段

```python
class StepSpec(_Base):
    id: str
    name: str | None = None
    action: ActionSpec
    check: CheckSpec | None = None
    retry: RetrySpec | None = None
    output_var: str | None = None
    
    # === 新增字段 ===
    condition: str | None = None      # if/else 条件表达式
    for_each: str | None = None       # for 循环列表表达式
    for_each_as: str = "item"         # 循环变量名
    for_index_as: str = "index"       # 索引变量名
```

### 4.2 StepResult 新增字段

```python
class StepResult(_Base):
    step_id: str
    status: StepStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    action_output: Any | None = None
    check_passed: bool | None = None
    error: str | None = None
    
    # === 新增字段 ===
    skipped_reason: str | None = None  # 跳过原因（condition_false / empty_for_each_list）
    parent_step_id: str | None = None  # 父 step ID（用于 for 循环子步骤）
    iteration_index: int | None = None # 迭代索引（用于 for 循环子步骤）
```

### 4.3 StepStatus 扩展

```python
StepStatus = Literal["success", "failed", "skipped"]
# 已支持 skipped，无需修改
```

## 5. 对 runner.py 的修改建议

### 5.1 新增条件表达式解析函数

```python
def evaluate_condition(condition: str | None, context: dict[str, Any]) -> bool:
    """
    评估条件表达式，返回 True/False
    
    支持的语法：
    - {{vars.X}} == 'value'
    - {{steps.X.output}} > 10
    - {{vars.a}} == 1 and {{vars.b}} == 2
    """
    if not condition:
        return True
    
    # 1. 先解析所有模板变量
    resolved = resolve_templates_in_condition(condition, context)
    
    # 2. 使用安全的 eval 评估表达式
    # 限制可用的操作符和函数
    allowed_names = {
        "true": True,
        "false": False,
        "null": None,
        "empty": lambda x: not x or len(x) == 0 if hasattr(x, "__len__") else not x,
        "contains": lambda x, y: y in x if x else False,
        "len": len,
    }
    
    try:
        result = eval(resolved, {"__builtins__": {}}, allowed_names)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Condition evaluation failed: {condition}, resolved: {resolved}, error: {e}")


def resolve_templates_in_condition(condition: str, context: dict[str, Any]) -> str:
    """
    解析条件表达式中的模板变量，返回可 eval 的字符串
    """
    def replace_template(match):
        template = match.group(1).strip()
        value = resolve_template_value(template, context)
        return repr(value)  # 使用 repr 确保字符串正确转义
    
    return re.sub(r'\{\{(.+?)\}\}', replace_template, condition)


def resolve_template_value(template: str, context: dict[str, Any]) -> Any:
    """
    解析单个模板变量，返回原始值
    """
    # {{steps.X.output}}
    steps_match = re.match(r'^steps\.(\w+)\.output$', template)
    if steps_match:
        step_id = steps_match.group(1)
        return context.get("steps", {}).get(step_id)
    
    # {{vars.X}}
    vars_match = re.match(r'^vars\.(\w+)$', template)
    if vars_match:
        var_name = vars_match.group(1)
        return context.get("vars", {}).get(var_name)
    
    # {{input}}
    if template == "input":
        return context.get("input")
    
    # {{item}}, {{index}} (for 循环内)
    if template in ("item", "index"):
        return context.get("forEach", {}).get(template)
    
    # {{forEach.item}}, {{forEach.index}}
    foreach_match = re.match(r'^forEach\.(\w+)$', template)
    if foreach_match:
        key = foreach_match.group(1)
        return context.get("forEach", {}).get(key)
    
    return None
```

### 5.2 修改 run_flow 方法

```python
def run_flow(self, flow: FlowSpec, *, input: Any | None = None, vars: dict[str, Any] | None = None) -> RunResult:
    # ... 初始化代码保持不变 ...
    
    for step in flow.steps:
        # === 新增：条件判断 ===
        if step.condition is not None:
            condition_passed = evaluate_condition(
                step.condition, 
                {"steps": step_outputs, "vars": runtime_vars, "input": current_input}
            )
            if not condition_passed:
                # 创建 skipped step result
                step_result = StepResult(
                    step_id=step.id,
                    status="skipped",
                    started_at=_utc_now(),
                    finished_at=_utc_now(),
                    duration_ms=0,
                    skipped_reason="condition_false",
                )
                run.steps.append(step_result)
                self._store.save_run(run)
                continue  # 跳过此 step，继续执行后续步骤
        
        # === 新增：for 循环处理 ===
        if step.for_each is not None:
            items = resolve_templates(step.for_each, {"steps": step_outputs, "vars": runtime_vars, "input": current_input})
            
            if not isinstance(items, list):
                raise TypeError(f"for_each must resolve to a list, got {type(items).__name__}")
            
            if len(items) == 0:
                # 空列表，标记为 skipped
                step_result = StepResult(
                    step_id=step.id,
                    status="skipped",
                    started_at=_utc_now(),
                    finished_at=_utc_now(),
                    duration_ms=0,
                    skipped_reason="empty_for_each_list",
                )
                run.steps.append(step_result)
                self._store.save_run(run)
                continue
            
            # 执行循环
            parent_step_started = _utc_now()
            all_success = True
            last_output = None
            
            for idx, item in enumerate(items):
                # 构建循环上下文
                loop_context = {
                    "steps": step_outputs,
                    "vars": runtime_vars,
                    "input": current_input,
                    "forEach": {
                        step.for_each_as: item,
                        step.for_index_as: idx,
                    }
                }
                
                # 执行单次迭代
                child_result = self._execute_single_step(
                    step=step,
                    context=loop_context,
                    run_id=run_id,
                    run_artifacts_dir=run_artifacts_dir,
                    parent_step_id=step.id,
                    iteration_index=idx,
                )
                
                run.steps.append(child_result)
                self._store.save_run(run)
                
                if child_result.status == "failed":
                    all_success = False
                    break
                
                last_output = child_result.action_output
            
            # 创建父 step 结果
            parent_step_finished = _utc_now()
            parent_result = StepResult(
                step_id=step.id,
                status="success" if all_success else "failed",
                started_at=parent_step_started,
                finished_at=parent_step_finished,
                duration_ms=int((parent_step_finished - parent_step_started).total_seconds() * 1000),
                action_output=last_output if all_success else None,
            )
            # 注意：父 step 不加入 run.steps，或者作为汇总记录
            # 可选：将子 step 结果嵌套到父 step 中
            
            if not all_success:
                # 循环失败，终止流程
                finished_at = _utc_now()
                run.status = "failed"
                run.finished_at = finished_at
                run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                run.error = f"for_each loop failed at iteration {idx}"
                self._store.save_run(run)
                return run
            
            # 记录输出
            step_outputs[step.id] = last_output
            if step.output_var is not None:
                runtime_vars[step.output_var] = last_output
            
            current_input = last_output
            continue
        
        # === 原有单 step 执行逻辑 ===
        step_result = self._execute_single_step(
            step=step,
            context={"steps": step_outputs, "vars": runtime_vars, "input": current_input},
            run_id=run_id,
            run_artifacts_dir=run_artifacts_dir,
        )
        
        # ... 后续处理保持不变 ...
```

### 5.3 新增 _execute_single_step 方法

```python
def _execute_single_step(
    self,
    step: StepSpec,
    context: dict[str, Any],
    run_id: str,
    run_artifacts_dir: Path,
    parent_step_id: str | None = None,
    iteration_index: int | None = None,
) -> StepResult:
    """
    执行单个 step，支持普通 step 和 for 循环子 step
    """
    step_started = _utc_now()
    step_error: str | None = None
    action_output: Any | None = None
    check_passed: bool | None = None
    
    attempts = step.retry.attempts if step.retry else 0
    backoff = step.retry.backoff_seconds if step.retry else 0.0
    
    for attempt in range(max(1, attempts + 1)):
        try:
            # 解析 action params 中的模板变量
            resolved_params = resolve_templates(
                step.action.params,
                context
            )
            
            action = self._registry.get_action(step.action.type)
            action_output = action(
                ActionContext(
                    run_id=run_id,
                    step_id=step.id,
                    input=context.get("input"),
                    vars=context.get("vars", {}),
                    artifacts_dir=run_artifacts_dir,
                ),
                resolved_params,
            )
            
            if step.check is not None:
                check = self._registry.get_check(step.check.type)
                check_passed = check(
                    CheckContext(
                        run_id=run_id,
                        step_id=step.id,
                        action_output=action_output,
                        vars=context.get("vars", {}),
                    ),
                    step.check.params,
                )
                if not check_passed:
                    raise RuntimeError(f"check failed: {step.check.type}")
            
            step_error = None
            break
            
        except Exception as e:
            step_error = str(e)
            if attempt >= attempts:
                break
            if backoff > 0:
                time.sleep(backoff * (2**attempt))
    
    step_finished = _utc_now()
    status: StepStatus = "success" if step_error is None else "failed"
    
    action_output = externalize_if_large(
        action_output, 
        artifacts_dir=run_artifacts_dir, 
        file_stem=f"{step.id}.{iteration_index}.action_output" if iteration_index is not None else f"{step.id}.action_output"
    )
    
    return StepResult(
        step_id=f"{step.id}[{iteration_index}]" if iteration_index is not None else step.id,
        status=status,
        started_at=step_started,
        finished_at=step_finished,
        duration_ms=int((step_finished - step_started).total_seconds() * 1000),
        action_output=action_output,
        check_passed=check_passed,
        error=step_error,
        parent_step_id=parent_step_id,
        iteration_index=iteration_index,
    )
```

## 6. 核心设计决策

### 6.1 条件表达式使用字符串而非结构化对象

**决策**：`condition` 使用字符串表达式 `"{{vars.env}} == 'prod'"`，而非结构化对象如 `{"var": "env", "op": "==", "value": "prod""}`。

**理由**：
- 更直观，用户可以直接阅读和理解
- 灵活性高，支持复杂逻辑组合
- 与现有模板语法保持一致

**风险与缓解**：
- 风险：需要安全地 eval 表达式
- 缓解：限制 eval 环境，只允许比较/逻辑运算符和特定函数

### 6.2 for 循环子 step 扁平化存储

**决策**：for 循环的每次迭代作为独立的 StepResult 存储，使用 `step_id[ index ]` 格式命名。

**理由**：
- 保持执行记录的可观测性
- 便于调试和追踪单个迭代的问题
- 与现有存储结构兼容

**替代方案**：嵌套存储（未采用）
- 缺点：需要修改存储结构，增加复杂性

### 6.3 skipped 状态不影响流程继续

**决策**：condition 为 false 或 for_each 为空列表时，step 标记为 `skipped`，但流程继续执行。

**理由**：
- 符合用户直觉：条件不满足 = 不需要执行 ≠ 失败
- 避免不必要的错误处理
- 与 GitHub Actions 等主流 CI/CD 工具行为一致

### 6.4 for 循环变量命名可配置

**决策**：提供 `for_each_as` 和 `for_index_as` 字段，允许用户自定义循环变量名。

**理由**：
- 避免变量名冲突（如嵌套循环场景）
- 提高可读性（`{{user}}` 比 `{{item}}` 更清晰）
- 默认值为 `"item"` 和 `"index"`，保持简单场景的简洁性

### 6.5 循环失败即终止

**决策**：for 循环中任一迭代失败，整个循环终止，流程失败。

**理由**：
- 默认安全：避免在错误状态下继续执行
- 简单明确：易于理解和预测
- 未来可扩展：可添加 `continue_on_error` 字段支持容错模式

## 7. 向后兼容性

- 所有新增字段均为可选，默认值为 `None` 或合理默认值
- 现有 Flow YAML 无需任何修改即可在新版本上运行
- 新增状态 `skipped` 已存在于 `StepStatus` 类型中

## 8. 未来扩展方向

1. **continue_on_error**: 允许 for 循环在单个迭代失败时继续
2. **parallel**: 支持 for 循环并行执行
3. **while 循环**: 基于条件的循环
4. **嵌套控制流**: if 嵌套在 for 中，或 for 嵌套在 if 中
5. **break/continue**: 循环控制语句

---

*文档结束*
