# 设计:插件共性层与后端去重优化

- 日期:2026-08-11
- 状态:已批准(设计评审)
- 前置:2026-08-10 四阶段代码库优化(#19)已完成,本次为其延续,聚焦后端与插件

## 1. 背景与目标

上一轮优化完成了 Plugin 基类 ABI 的首次统一(hooks.py → `PLUGIN` 导出),但共性层仍不完整,存在三类重复:

1. **配置获取三套重复**:zhihu `_get_cookie`、ai_deepseek `_get_deepseek_api_key`、openclaw 模块级 `_DEFAULTS/_SECRETS`(`clear()+update()` 注入,全局可变状态反模式)各自实现了一套 secrets/配置解析。
2. **dry_run 样板重复**:desktop_checkin 8 个 action 几乎每个都有手写的 `if dry_run_enabled(...)` 判定与 dry_run 结果构造;zhihu、ai_deepseek 同样。
3. **后端运行时代码重复**:runner.py 中模板解析 context `{"steps":..., "vars":..., "input":...}` 在 4 处重复构造(condition / for_each / action params / hooks);`StepResult` 构造在 skipped 与正常两处重复;registry.py 头注释已过时("基于 Hook 模式");setting_manager 中 argparse 默认值与 config 默认值重复。

**目标**:通过共性层变更统一上述模式,提升插件开发体验与后端可维护性。

**范围约束**:
- 只做共性变更(基类/helpers/共享模式),不特化任何单个插件行为
- 插件 action/check 的**返回值结构(API 契约)不变**,只收敛判定与配置访问方式
- HTTP API、plugins.yaml、config.yaml 结构、前端、loader 逻辑均不变
- 不引入新依赖

## 2. 调研结论(设计依据)

| 来源 | 结论 | 对本设计的影响 |
|---|---|---|
| python-patterns.guide(Prebound Method / Global Object) | 模块级共享状态应封装进类实例;全局可变状态是反模式,破坏测试隔离 | openclaw `_DEFAULTS/_SECRETS` 改为实例级 `self.defaults/self.secrets`;handlers 改实例方法 |
| stevedore(OpenStack 插件框架) | 插件类由宿主(loader)实例化并管理生命周期;加载/注册与插件本体职责分离 | loader 保持 `plugin_cls(config)` + `register()` 不变,只同步注释 |
| Ansible check mode | dry-run = 全局开关 + 任务级覆盖 两级模型 | `is_dry_run` 判定链 `params.dry_run > ctx.vars.dry_run > env` 与之对应 |
| pydantic-settings | 配置分层优先级:init kwargs > env > dotenv > secrets > defaults,高层覆盖低层 | `setting()` 取值链 `params > defaults > secrets > env_var > default` 为同一理念的适配 |
| 12-factor(Config) | 凭据属配置,严格分离配置与代码,存环境变量 | config.yaml `secrets:` 块 env 引用机制保持不变,只统一访问入口 |

## 3. 插件共性层设计

### 3.1 Plugin 基类(plugins/common/plugin.py)

```python
class Plugin:
    name: str
    version: str = "0.1.0"
    dry_run_env: str | None = None      # 新增:dry_run 部署级环境变量名(替代各插件模块级 _DRY_RUN_ENV 常量)

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))   # 实例级,替代 openclaw 模块级 _DEFAULTS
        self.secrets = dict(self.config.get("secrets", {}))     # 实例级,替代模块级 _SECRETS
        self.actions: dict[str, ActionHandler] = {}             # 实例属性,子类 __init__ 绑定实例方法
        self.checks: dict[str, CheckHandler] = {}

    def register(self, registry: Registry) -> None:
        """注册元信息、actions、checks(逻辑不变,遍历 self.actions/self.checks)"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)

    # ---- 新增共性 API ----

    def is_dry_run(self, ctx: ActionContext, params: dict[str, Any]) -> bool:
        """统一 dry_run 判定:params.dry_run > ctx.vars.dry_run > 环境变量 self.dry_run_env"""
        # 保留原 helpers.dry_run_enabled 的语义(env 参数改为读取 self.dry_run_env)

    def setting(self, params: dict[str, Any], key: str, *, env_var: str | None = None,
                default: Any = None) -> Any:
        """统一取值链:params[key] > self.defaults[key] > self.secrets[key] > os.getenv(env_var) > default
        env_var 仅当调用方显式指定时参与(secrets 已含 env 解析结果,避免重复)。
        值为 str 且 strip() 为空时视为未设置,继续向下一层回退(与 zhihu _get_cookie 现有语义一致);
        返回值为 str 且以 "env:" 前缀开头时,按 resolve_env_value 解析为环境变量值。"""

    def error_result(self, error: str, *, error_type: str = "unknown_error",
                     **fields: Any) -> dict[str, Any]:
        """统一错误返回构造:{"error":..., "error_type":..., **fields}"""
```

要点:
- `actions`/`checks` 由类属性改为实例属性,`register()` 行为不变
- `is_dry_run` 采用**优先级语义**(实施确认):params 键存在即以 params 值定夺(显式 `dry_run: False` 覆盖 vars/env),否则依次检查 vars.dry_run、环境变量 dry_run_env。与旧 `helpers.dry_run_enabled`(truthy OR 链)的差异:params 显式 False 可覆盖低层开关——属有意设计(任务级强制),由 `test_params_override_env`/`test_params_false_overrides_vars_true` 固化
- `error_result` 不强制 schema,只统一构造入口

### 3.2 helpers(plugins/common/helpers.py)

- **移除**:`dry_run_enabled`(迁移为基类方法 `is_dry_run`)
- **保留**:`is_truthy`、`read_text`、`write_text`、`utc_now_iso`、`safe_name`
- **新增**:`error_result` 纯函数版(与基类方法同实现,供非类内使用);`resolve_env_value(value)`(若为 str 且以 `"env:"` 开头则返回 `os.getenv(value[4:])`,否则原样返回;被 `setting()` 内置调用,也可独立使用)

### 3.3 handlers 类方法形态(迁移模式)

```python
class DesktopCheckinPlugin(Plugin):
    """桌面自动打卡插件"""

    name = "desktop-checkin"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_DESKTOP_DRY_RUN"

    def __init__(self, config=None):
        super().__init__(config)
        self.actions = {
            "desktop.activate_window": self._activate_window,
            "desktop.click": self._click,
            "desktop.double_click": self._double_click,
            "desktop.drag": self._drag,
            "desktop.type_text": self._type_text,
            "desktop.hotkey": self._hotkey,
            "desktop.wait": self._wait,
            "desktop.screenshot": self._screenshot,
        }
        self.checks = {
            "desktop.image_exists": self._image_exists,
            "desktop.window_title_contains": self._window_title_contains,
        }

    def _activate_window(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        if self.is_dry_run(ctx, params):
            return {"activated": True, ..., "dry_run": True}
        ...
```

迁移规则(适用于全部 5 插件 + 2 examples):
1. 模块级 handler 函数 → 实例方法,首参从 `ctx` 前插入 `self`
2. 模块级 `_DRY_RUN_ENV` 常量 → 类属性 `dry_run_env`
3. `dry_run_enabled(ctx, params, _DRY_RUN_ENV)` → `self.is_dry_run(ctx, params)`
4. secrets/config 读取 → `self.setting(params, key, env_var=..., default=...)`:
   - zhihu `_get_cookie` → `self.setting(params, "cookie", env_var="ZHIHU_COOKIE")`(`env:` 前缀解析由 `setting()` 内置的 `resolve_env_value` 统一处理;`cookie_env` 参数语义保留:先查 `params["cookie_env"]` 环境变量名,再按同名环境变量取值)
   - ai_deepseek `_get_deepseek_api_key` → `self.setting(params, "api_key", env_var="DEEPSEEK_API_KEY")`,缺失时 raise RuntimeError 的行为保留
   - openclaw `_DEFAULTS.get(...)` → `self.defaults.get(...)`;`_SECRETS.get(...)` → `self.secrets.get(...)`(模块级变量删除)
5. openclaw 错误返回 → `self.error_result(...)`(字段名与 error_type 值不变)
6. `PLUGIN = XxxPlugin` 导出保持不变;actions/checks dict 从类属性移到 `__init__`

### 3.4 插件迁移清单

| 插件 | 文件 | 迁移内容 |
|---|---|---|
| dummy | plugins/dummy/backend.py | 方法化,无 dry_run/secrets |
| desktop_checkin | plugins/desktop_checkin/backend.py | 方法化 + dry_run_env + is_dry_run(8 actions) |
| zhihu_digest | plugins/zhihu_digest/backend.py | 方法化 + _get_cookie 收敛为 setting() |
| ai_deepseek | plugins/ai_deepseek/backend.py | 方法化 + _get_deepseek_api_key 收敛 + DeepSeekClient 保持 |
| openclaw | plugins/openclaw/backend.py | 方法化 + 删模块级 _DEFAULTS/_SECRETS + error_result |
| examples | plugins/examples/hello_world.py、dummy_echo.py | 方法化对齐新样板 |

## 4. 后端去重设计

### 4.1 runner.py

- 提取 `_template_context(step_outputs, runtime_vars, current_input) -> dict` 消除 4 处重复构造(condition / for_each / action params / hooks)
- `run_flow` 中 skipped 与正常两处 `StepResult` 构造收敛为一个私有工厂 `_make_step_result(...)`
- 失败路径逻辑保持不变,仅减少结构重复
- 行为零变化(纯重构)

### 4.2 registry.py

- 头注释更新:删除"基于 Hook 模式"过时描述,改为 Plugin 注册表描述
- 无逻辑变更

### 4.3 setting_manager.py

- 收敛 `init()` 中 `getattr(args, x, default)` 三连重复与 `_load_env` 中部分重复默认值(如 `PORT` 双处定义)
- 行为零变化(纯重构)

### 4.4 plugin_loader.py

- 逻辑不变;docstring/注释同步新 ABI(类方法形态)描述

## 5. 测试策略

- **现有测试**:95 个测试全部保持通过(插件测试 3 个文件适配类方法形态;后端测试不应需要改动)
- **新增测试**:
  - Plugin 基类单测:`is_dry_run` 判定链(参数/环境变量/默认关闭)、`setting()` 取值链全层级(env_var 显式参与、defaults/secrets 覆盖、缺失回退)、`error_result` 构造
  - 迁移后各插件 action 单测保持(现有 desktop_checkin/zhihu_digest 测试适配)
- **验证命令**:`pytest`(backend 目录,目标 95+ 通过)、`ruff check`、`ruff format --check`、插件加载冒烟(6 插件注册)

## 6. 文档同步

- `docs/zh/plugin-dev-guide.md`:新 ABI 示例(类方法形态、is_dry_run、setting、error_result)
- `docs/en/plugin-dev-guide.md`:同上
- `docs/zh/specs/plugin-sdk.md`:协议描述更新

## 7. 验证标准

1. pytest 全绿(≥95,含新增基类测试)
2. ruff check + format 通过
3. 后端启动冒烟:插件全部加载(6 插件 0 errors)、/plugins、/runs/execute 正常
4. 迁移后无残留:grep 无 `_DRY_RUN_ENV`、`_DEFAULTS`、`_SECRETS`、`dry_run_enabled` 引用
5. docs 无旧 ABI 示例残留
6. 零新依赖;HTTP API 契约不变

## 8. 范围外(不做)

- 前端任何改动
- 插件 action 返回值结构变更
- loader/plugins.yaml/config.yaml 结构变更
- 新依赖引入
- 未覆盖功能的性能优化
