# Proposal: Plugin Configuration System

## Why

当前 AutoFlow 插件的配置管理存在严重缺陷：

1. **配置与代码脱节**：`config.yaml` 中明确定义了 `base_url`、`timeout` 等配置项，但 `backend.py` 完全忽略这些配置，所有值都是硬编码
2. **多环境切换困难**：开发、测试、生产环境需要不同的 API 端点和超时设置，硬编码导致每次切换环境都需要修改代码
3. **缺乏灵活性**：用户无法通过配置文件自定义插件行为，降低了插件的可配置性和可维护性

## What Changes

### 1. 插件初始化时读取 config.yaml

修改 `plugins/openclaw/backend.py` 的 `__init__` 方法：

- 在初始化时加载 `config.yaml` 文件
- 解析 `plugins.openclaw` 部分的配置项
- 支持环境变量覆盖配置值（优先级：环境变量 > 配置文件 > 硬编码默认值）

### 2. Action 方法优先使用配置值

修改各 action 方法（如 `call_api`、`execute` 等）：

- 从配置中读取 `base_url`、`timeout`、`retry_count` 等参数
- 如果配置不存在，使用硬编码默认值作为兜底
- 支持运行时通过参数覆盖配置值

### 3. 配置结构示例

```yaml
plugins:
  openclaw:
    base_url: "https://api.example.com"
    timeout: 30
    retry_count: 3
    verify_ssl: true
```

## Scope

涉及文件：

- `plugins/openclaw/backend.py` - `__init__` 方法和各 action 方法
- `config.yaml` - 配置结构定义（已存在，需确保格式兼容）

## Rollback Plan

1. **保留硬编码默认值**：所有配置项都有硬编码默认值，配置读取失败时自动降级使用默认值
2. **异常捕获**：配置读取逻辑包裹在 try-except 中，任何异常都不会影响插件正常启动
3. **配置验证**：增加配置项有效性检查，无效配置值使用默认值替代并记录警告日志

## Success Criteria

1. ✅ `backend.py` 能够正确读取 `config.yaml` 中的配置项
2. ✅ 配置值优先级正确：环境变量 > 配置文件 > 硬编码默认值
3. ✅ 配置读取失败时，插件仍能正常启动并使用默认值
4. ✅ 所有 action 方法优先使用配置值而非硬编码值
5. ✅ 多环境切换只需修改配置文件，无需改动代码
6. ✅ 单元测试覆盖配置读取和降级逻辑
