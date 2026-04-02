# Tasks: exec-security-hardening

## Task 1: 更新 config.yaml

- [ ] 新增 `safe_mode` 配置项（bool，默认 false）
- [ ] 新增 `allowed_commands` 配置项（正则列表，可选，空列表表示不限制）

## Task 2: 支持 command/args 分离

- [ ] 修改 `exec_command` 方法，新增可选参数 `args: list[str]`
- [ ] 当 `args` 存在时，使用 `[command] + args` 列表形式调用

## Task 3: 实现 safe_mode 逻辑

- [ ] 读取 `self.config.get("safe_mode", False)`
- [ ] safe_mode=True 时：使用 `shlex.split(command)` + `shell=False`
- [ ] safe_mode=False 时：保持原有 `shell=True` 行为（向后兼容）

## Task 4: 实现命令白名单校验

- [ ] 读取 `allowed_commands` 配置（正则列表）
- [ ] 若列表非空，校验命令是否匹配任一正则
- [ ] 不匹配时返回错误：`{"exit_code": -1, "error": "command not allowed"}`

## Task 5: 更新测试

- [ ] 新增测试：safe_mode=True 时正常命令可执行
- [ ] 新增测试：safe_mode=True 时命令注入被阻断
- [ ] 新增测试：allowed_commands 白名单生效
- [ ] 新增测试：command/args 分离模式正常工作

## Task 6: 更新 plugin.yaml

- [ ] 在 `config_schema` 中补充 `safe_mode` 和 `allowed_commands` 字段说明
