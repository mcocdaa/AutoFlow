---
title: 代码库优化重构设计
description: 插件/后端/前端/文档四阶段代码优化与整理
version: "1.0"
keywords: [refactor, plugin-sdk, backend, frontend, docs]
---

# 代码库优化重构设计

## 1. 背景与目标

AutoFlow 经过多轮迭代后,插件层、后端、前端、文档存在以下问题:

- **插件层重复最严重**:4 个插件的 `hooks.py` 逐字节相同(register 样板);`_is_truthy`/`_dry_run`/路径读写等工具函数在多个插件中复制粘贴;每个插件手工维护 `name/version/actions/checks` dict。
- **后端**:store 与 runner 存在三处重叠的深拷贝/序列化逻辑;模型映射存在样板;`setting_manager` 有一批从未使用的 DB/Redis 死配置。
- **前端**:两个 store 的 loading/error 样板重复;错误提取逻辑分散;api 层未类型化。
- **文档**:插件开发指南基于旧的 register 协议,重构后必须同步;docs/en 与 docs/zh 存在缺失与不一致。

**目标**:强化代码复用性、清晰化、架构的清洁/可扩展/复用/灵活。

**顺序**:插件 → 后端 → 前端 → 文档(依赖链:插件 ABI 定稿 → 后端随之调整 → 前端消费 → 文档统一)。

## 2. 约束

- 插件注册 ABI **不保留兼容层**,仓库内插件全部迁移到新协议。
- 后端 HTTP API(`/api/v1/*` 接口与响应模型)**保持兼容**,前端与外部调用方不受影响。
- **不引入新的第三方依赖**(后端/前端/插件均如此)。
- 每个阶段独立提交、独立验证,验证通过才进入下一阶段。

## 3. 阶段一:插件层 — Plugin 基类新 ABI

### 3.1 新增 plugins/common/

```
plugins/common/
├── __init__.py      # 导出 Plugin 与 helpers
├── plugin.py        # Plugin 抽象基类
└── helpers.py       # 共享工具函数
```

`plugins/common` 不注册进 `plugins.yaml`,不会被 loader 当作插件加载;loader 只加载注册表中启用的条目。

### 3.2 Plugin 基类

```python
class Plugin:
    """插件基类:声明式元信息 + 统一注册"""

    name: str
    version: str = "0.1.0"
    actions: dict[str, ActionHandler] = {}
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def register(self, registry: Registry) -> None:
        """注册 plugin 元信息、actions、checks(替代 hooks.py 样板)"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)
```

- `ActionHandler`/`CheckHandler` 类型沿用 `app.core.registry` 的定义。
- actions/checks 以**类属性**声明,handler 为模块级函数或 `@staticmethod`(类体内无法引用实例方法);实例方法场景在迁移时改为模块级函数。
- 插件模块暴露 `PLUGIN = XxxPlugin`(类引用),由 loader 实例化并注入 config。
- 插件结构收敛为:

```
插件目录/
├── __init__.py       # 导出 PLUGIN
├── backend.py        # class XxxPlugin(Plugin),actions/checks 以类属性声明
└── config.yaml       # 可选,defaults + secrets
```

文件插件(如 examples/*.py)直接在单文件中定义类与 `PLUGIN`。

### 3.3 helpers 清单(去重)

| 函数 | 来源 | 说明 |
|------|------|------|
| `is_truthy(v)` | desktop/zhihu 重复 | 布尔化判定 |
| `dry_run_enabled(ctx, params, env_var)` | desktop/zhihu 重复 | 统一 dry_run 判定(env 变量名参数化) |
| `read_text(ctx, path, extra_roots=())` | zhihu/ai_deepseek/desktop | 安全路径读取(防穿越) |
| `write_text(ctx, rel_path, text)` | zhihu/ai_deepseek/desktop | 写入 artifacts 目录 |
| `utc_now_iso()` | zhihu | UTC ISO 时间戳 |
| `safe_name(name, fallback)` | desktop | 文件名净化 |

### 3.4 迁移清单

| 插件 | 现状 | 迁移动作 |
|------|------|----------|
| dummy | backend.py + hooks.py | hooks.py 删除,backend.py 改为 Plugin 子类 |
| desktop_checkin | backend.py + hooks.py | 同上;工具函数换 helpers |
| zhihu_digest | backend.py + hooks.py | 同上 |
| ai_deepseek | backend.py + hooks.py | 同上 |
| openclaw | backend.py + hooks.py(构造接收 config) | 同上;config 经构造注入 |
| examples/hello_world.py | register 函数 | 改为 Plugin 子类 + PLUGIN |
| examples/dummy_echo.py | register 函数 | 同上 |
| plugins/index.md | 旧协议文档 | 更新为新 ABI 说明 |

`openclaw_plugin` 子模块(JS 插件)不受影响,仅 Python 壳迁移。

### 3.5 阶段验证

- `backend/tests/test_plugin_loader.py` 适配新加载逻辑,并补充用例:PLUGIN 识别、config 注入、无 PLUGIN 时错误上报。
- 全部 pytest 通过;启动冒烟:`GET /api/v1/plugins` 仍返回 6 个插件;`/runs/execute` 执行冒烟通过。

## 4. 阶段二:后端

### 4.1 plugin_loader 演进

- 识别插件模块导出的 `PLUGIN`(Plugin 子类),实例化并注入 `_load_plugin_config` 解析结果,调用 `plugin.register(registry)`。
- 删除 `getattr(module, "register")` 协议;模块名解析逻辑保留(目录/文件两种形态)。
- 加载失败行为不变:记录到 `registry.add_plugin_error`,不影响其他插件。

### 4.2 序列化/深拷贝统一

新增 `backend/app/runtime/utils/serialization.py`:

- `safe_deep_copy(value)`:替换 store.`_deep_copy_with_ref_tracking` 与 runner.`_deep_copy_or_str`。
- `to_jsonable(value)`:JSON 往返打断循环引用(替换 runner.`_to_vars_value`)。
- store 与 runner 改为引用统一实现,删除私有重复函数。

### 4.3 模型映射去样板

- `plugin/models.py` 的 `PluginItem` 增加 `from_info(info: PluginInfo)` 工厂方法;`PluginErrorItem` 同样处理。
- `api/v1/plugins.py` 的推导式收拢为工厂调用。

### 4.4 死代码清理

- `setting_manager.py`:grep 确认无引用后删除 DB/Redis 配置项(DB_HOST/DB_PORT/DB_USER/DB_NAME/DB_PASSWORD/REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_URL/SECRET_KEY 等)与对应 `REDIS_URL` 拼接。
- 保留端口配置(BACKEND_*/FRONTEND_* 等被 compose/start.sh 使用)。
- `env_secrets.py` 的 allowlist 同步核对(仅保留实际使用的 secret)。

### 4.5 阶段验证

- 全部 pytest 通过(含 plugins 目录测试)。
- 启动冒烟:`/health`、`/plugins`、`/runs/execute` 正常;配置日志无缺失引用。

## 5. 阶段三:前端(数据层 + 状态层)

### 5.1 api 层增强

- `src/api/index.ts`:新增 axios 响应拦截器,统一错误标准化 —— 优先提取 `response.data.detail`,兜底 `Error.message`;store 不再各自写提取逻辑。
- 新增类型化接口函数:
  - `src/api/plugins.ts`:`fetchPlugins(): Promise<PluginsResponse>`
  - `src/api/runs.ts`:`executeFlow(flowYaml, input, vars): Promise<RunResult>`、`fetchRun(runId): Promise<RunResult>`
  - 类型复用现有 `src/types/plugins.ts`、`src/types/runs.ts`。

### 5.2 状态层重构

- 新增 `src/composables/useAsyncState.ts`:泛型封装 `{ data, loading, error, execute }`,try/catch/finally 样板收敛一处。
- `stores/plugins.ts`、`stores/runs.ts` 改为 setup store 风格 + useAsyncState(兼容现有视图用法,响应式状态不变)。
- 类型层核对,消除重复声明。

### 5.3 阶段验证

- `npm run build:web`(vue-tsc 严格模式)通过。
- 启动冒烟:插件列表、执行流程、错误路径(detail 提取)验证。

## 6. 阶段四:文档

### 6.1 插件开发指南重写

- `docs/zh/plugin-dev-guide.md`:改为 Plugin 基类新 ABI —— 无 hooks.py、`PLUGIN` 约定、helpers 用法、最小示例。
- 检查 `docs/zh/specs/plugin-sdk.md` 与指南的重叠,重叠则合并去重。
- 新增 `docs/en/plugin-dev-guide.md`(当前 en 无对应文件)。

### 6.2 对齐与补全

- docs/en ↔ docs/zh 的架构/后端/前端/模块文档更新为重构后结构(插件目录变化、backend 模块变化)。
- 规范统一:文件头模板(遵循 docs/rules/docs.md 的 6 行 YAML 头部)、目录结构、术语一致性检查。

### 6.3 openspec 变更记录

- 四个阶段各记录一条变更(openspec/changes 或归档,按仓库既有约定)。

### 6.4 阶段验证

- 文档规范检查:每个目录 index.md 存在、头部格式符合 docs/rules/docs.md。
- 指南中的示例代码与最终实现一致(示例可在 python REPL 中导入验证)。

## 7. 风险与回滚

- **插件 ABI 不兼容**:仓库内迁移一次性完成;外部使用者需参考新指南(文档阶段输出)。
- **openclaw 子模块**:不修改其内部,仅迁移 Python 壳;子模块指针不动。
- **回滚**:每个阶段独立 commit,可逐阶段 revert。

## 8. 验收标准

- 插件目录无重复样板:grep `def register\(registry` 在 plugins/ 下应为 0 命中(hooks.py 全部删除)。
- 后端无重复序列化函数:grep `_deep_copy` 仅剩 serialization.py 一处定义。
- 前端 store 无重复 loading/error 样板;vue-tsc 严格模式构建通过。
- 全部 pytest 通过;端到端冒烟(插件列表 + 执行)通过。
- 文档与代码结构一致,无旧协议残留描述(全文 grep `register(registry)` 仅历史记录/指南中说明迁移)。
