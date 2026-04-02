# Proposal: Exec Security Hardening

## Why

当前 `openclaw.exec` 实现存在严重的安全隐患：

1. **命令注入风险**：使用 `shell=True` 执行命令，用户输入未经充分过滤直接拼接到命令字符串中，存在命令注入攻击风险
2. **无命令白名单**：允许执行任意系统命令，包括危险操作（如 `rm -rf /`、`format` 等）
3. **生产环境不安全**：在生产环境中，任意命令执行可能导致数据泄露、系统损坏或服务中断
4. **缺乏审计追踪**：无法记录和追踪执行的命令，难以进行安全审计

## What Changes

### 1. 增加 safe_mode 配置开关

修改 `config.yaml`：

- 新增 `exec.safe_mode` 配置项，默认值为 `false`
- 当 `safe_mode: true` 时，启用安全限制

### 2. 支持 command/args 分离模式

修改 `plugins/openclaw/backend.py` 的 `exec_command` 方法：

- 支持 `shell=False` 模式，使用列表形式的 `command` + `args`
- 示例：`["git", "clone", "https://github.com/user/repo.git"]`
- 避免 shell 注入风险

### 3. 可选命令白名单正则

在 `config.yaml` 中配置允许执行的命令白名单：

```yaml
exec:
  safe_mode: true
  allowed_commands:
    - "^git\s+(clone|pull|status|log).*"
    - "^python\s+.*\.py$"
    - "^pytest\s+.*"
  blocked_patterns:
    - "rm\s+-rf\s+/"
    - "format\s+"
    - "dd\s+if=.*of=/dev/"
```

### 4. 命令执行审计日志

- 记录所有执行的命令到审计日志
- 包含时间戳、执行用户、命令内容、执行结果

## Scope

涉及文件：

- `plugins/openclaw/backend.py` - `exec_command` 方法
- `config.yaml` - 新增 `exec` 配置段

## Rollback Plan

1. **safe_mode 默认关闭**：`safe_mode` 默认值为 `false`，不影响现有用法
2. **向后兼容**：保留原有的 `shell=True` 模式，通过参数控制切换
3. **渐进式启用**：用户可以逐步测试 safe_mode，确认无误后再全面启用
4. **白名单为空时允许所有**：如果未配置白名单且 safe_mode 关闭，保持现有行为

## Success Criteria

1. ✅ `safe_mode` 配置开关工作正常，默认关闭不影响现有功能
2. ✅ `shell=False` 模式下，命令和参数正确分离，无注入风险
3. ✅ 命令白名单正则匹配正确，未授权的命令被拒绝执行
4. ✅ 危险命令模式（如 `rm -rf /`）被正确拦截
5. ✅ 所有执行的命令被记录到审计日志
6. ✅ 向后兼容：现有 flow 无需修改即可继续运行
7. ✅ 安全测试覆盖：命令注入尝试被有效阻止
