# 阶段一:插件层 — Plugin 基类新 ABI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 plugins/ 下全部插件从旧 `register(registry)` 协议迁移到 `plugins/common` 的 Plugin 基类新 ABI(声明式类属性 + `PLUGIN` 导出 + 共享 helpers),适配加载器与测试,使 `/api/v1/plugins` 仍返回 6 个插件且全部 pytest 通过。

**Architecture:** 新增 `plugins/common/`(Plugin 基类 + 6 个去重 helpers,不注册进 plugins.yaml)。5 个目录插件与 2 个文件示例插件迁移为 `class XxxPlugin(Plugin)` 并在模块级导出 `PLUGIN`;hooks.py 全部删除。`plugin_loader.py` 做最小调整:识别 `PLUGIN`(Plugin 子类)并注入 config。迁移采用「过渡双协议」策略:先只改 backend.py(类属性使旧 hooks.register 依然有效),再切换 loader,最后删 hooks.py——保证每个 commit 全量测试保持绿色。

**Tech Stack:** Python 3.12、pytest 9、ruff 0.16(格式 `ruff format`,lint `ruff check`)、FastAPI/TestClient、pyyaml。命令统一从 `backend/` 目录执行 pytest 与 ruff;`plugins` 包位于仓库根目录,测试通过 `backend/tests/conftest.py` 把仓库根加入 `sys.path`。

---

## 0. 迁移策略与约定(先读)

1. **过渡双协议**:Task 6–10 只重写 `backend.py` 并让 `__init__.py` 临时同时导出 `register`(来自 hooks.py)与 `PLUGIN`。因为迁移后的 actions/checks/name/version 都是**类属性**,旧的 `hooks.register` 依旧正常工作(`plugin = XxxPlugin(); plugin.actions ...`),因此 loader 未切换前全量测试保持绿色。
2. **阶段二说明**:`plugin_loader.py` 的最终收敛(清理注释、docstring、进一步重构)属于阶段二。本计划只做「能加载新 ABI 插件」的最小调整,并在 Task 14 中注明阶段二再收敛。
3. **openclaw 的 config 注入**:handlers 必须是模块级函数(不能引用实例方法),而 handlers 需要 config 的 defaults/secrets。因此 `OpenClawPlugin.__init__` 把 config 写入模块级 `_DEFAULTS`/`_SECRETS` 供 handlers 读取。插件在进程启动时只加载一次(`get_registry` 为 `@lru_cache` 单例),该设计安全;不做 partial 绑定以避免破坏过渡期 hooks 协议。
4. **验收断言**(来自 spec 第 8 章):`grep -rn "def register(registry" plugins/` 命中 0(注意:docs/zh/plugin-dev-guide.md 中的旧协议描述属阶段四清理,不在本计划范围);全部 pytest 通过;冒烟 6 插件。
5. **commit 风格**:遵循仓库惯例,使用 `refactor(plugins):`、`refactor(backend):`、`docs(plugins):` 等前缀,每个任务独立 commit。

## 1. 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `plugins/common/__init__.py` | 导出 `Plugin` 与 6 个 helpers |
| `plugins/common/plugin.py` | `Plugin` 抽象基类(声明式 name/version/actions/checks + 统一 register) |
| `plugins/common/helpers.py` | 共享工具:is_truthy / dry_run_enabled / read_text / write_text / utc_now_iso / safe_name |
| `backend/tests/conftest.py` | 测试基座:把仓库根目录加入 `sys.path`,使测试与 loader 可导入 `plugins.*` |
| `backend/tests/test_plugin_common.py` | Plugin 基类 + helpers 的单元测试(TDD 驱动) |

### 修改

| 文件 | 职责 |
|------|------|
| `plugins/dummy/backend.py` | 改为 `DummyPlugin(Plugin)`,handler 改模块级函数,导出 `PLUGIN` |
| `plugins/dummy/__init__.py` | Task 6 双导出(register+PLUGIN),Task 15 只导出 `PLUGIN` |
| `plugins/desktop_checkin/backend.py` | 同上;`_is_truthy/_dry_run/_safe_name/_read_text/_write_text` 换 helpers |
| `plugins/desktop_checkin/__init__.py` | 同上 |
| `plugins/zhihu_digest/backend.py` | 同上;`_utc_now_iso/_is_truthy/_dry_run/_read_text/_write_text` 换 helpers |
| `plugins/zhihu_digest/__init__.py` | 同上 |
| `plugins/ai_deepseek/backend.py` | 同上;`_is_truthy/_dry_run/_read_text/_write_text/_repo_root` 换 helpers |
| `plugins/ai_deepseek/__init__.py` | 同上 |
| `plugins/openclaw/backend.py` | 同上;config 经构造注入(模块级 `_DEFAULTS/_SECRETS`) |
| `plugins/openclaw/__init__.py` | 同上 |
| `plugins/examples/hello_world.py` | 单文件:改为 Plugin 子类 + `PLUGIN`,删除 register 函数 |
| `plugins/examples/dummy_echo.py` | 同上 |
| `backend/app/runtime/plugin_loader.py` | 最小调整:识别 `PLUGIN`(Plugin 子类),注入 config,调用 `plugin.register` |
| `backend/tests/test_plugin_loader.py` | 适配新协议 + 新用例(PLUGIN 识别、config 注入、无 PLUGIN 错误上报) |
| `plugins/index.md` | 更新为新 ABI 说明 |

### 删除

| 文件 |
|------|
| `plugins/dummy/hooks.py`、`plugins/desktop_checkin/hooks.py`、`plugins/zhihu_digest/hooks.py`、`plugins/ai_deepseek/hooks.py`、`plugins/openclaw/hooks.py` |

> 说明:`plugins/common` 不注册进 `plugins.yaml`,loader 不会将其当作插件加载。`openclaw_plugin/` 子模块(JS 插件)不动。

---

## Task 1: 新增测试基座与 plugins/common 失败测试(TDD 红)

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_plugin_common.py`
- Test: `backend/tests/test_plugin_common.py`

- [ ] **Step 1: 创建 `backend/tests/conftest.py`**

```python
# @file /backend/tests/conftest.py
# @brief pytest 共享配置:将仓库根目录加入 sys.path,使插件包(plugins.*)可被测试与 loader 导入
# @create 2026-08-10

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
```

- [ ] **Step 2: 创建 `backend/tests/test_plugin_common.py`**

```python
# @file /backend/tests/test_plugin_common.py
# @brief plugins/common 单元测试:Plugin 基类注册行为 + 共享 helpers
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path

from app.core.registry import ActionContext, Registry
from plugins.common.helpers import (
    dry_run_enabled,
    is_truthy,
    read_text,
    safe_name,
    utc_now_iso,
    write_text,
)
from plugins.common.plugin import Plugin


def _ctx(artifacts_dir: Path) -> ActionContext:
    return ActionContext(
        run_id="run-1",
        step_id="step-1",
        input=None,
        vars={},
        artifacts_dir=artifacts_dir,
    )


class TestPluginBase:
    def test_register_registers_plugin_and_actions_checks(self) -> None:
        def _handler(ctx, params):
            return {}

        def _check(ctx, params):
            return True

        class SamplePlugin(Plugin):
            name = "sample"
            version = "2.0.0"
            actions = {"sample.run": _handler}
            checks = {"sample.ok": _check}

        registry = Registry()
        SamplePlugin().register(registry)

        assert [(p.name, p.version) for p in registry.list_plugins()] == [
            ("sample", "2.0.0")
        ]
        assert registry.list_actions() == ["sample.run"]
        assert registry.list_checks() == ["sample.ok"]

    def test_config_defaults_to_empty_dict(self) -> None:
        class SamplePlugin(Plugin):
            name = "sample"
            actions = {}

        p = SamplePlugin()
        assert p.config == {}

        p2 = SamplePlugin(config={"defaults": {"a": 1}})
        assert p2.config["defaults"] == {"a": 1}


class TestIsTruthy:
    def test_bool_values(self) -> None:
        assert is_truthy(True) is True
        assert is_truthy(False) is False

    def test_none_is_false(self) -> None:
        assert is_truthy(None) is False

    def test_string_values(self) -> None:
        assert is_truthy("1") is True
        assert is_truthy(" true ") is True
        assert is_truthy("yes") is True
        assert is_truthy("y") is True
        assert is_truthy("on") is True
        assert is_truthy("0") is False
        assert is_truthy("false") is False
        assert is_truthy("off") is False


class TestDryRunEnabled:
    def test_params_dry_run_wins(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        assert dry_run_enabled(ctx, {"dry_run": True}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_vars_dry_run(self, tmp_path: Path) -> None:
        ctx = ActionContext(
            run_id="r",
            step_id="s",
            input=None,
            vars={"dry_run": True},
            artifacts_dir=tmp_path,
        )
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_env_var(self, tmp_path: Path, monkeypatch) -> None:
        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is True

    def test_default_false(self, tmp_path: Path, monkeypatch) -> None:
        ctx = _ctx(tmp_path)
        monkeypatch.delenv("AUTOFLOW_TEST_DRY_RUN", raising=False)
        assert dry_run_enabled(ctx, {}, "AUTOFLOW_TEST_DRY_RUN") is False


class TestReadWriteText:
    def test_write_then_read_roundtrip(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        rel = write_text(ctx, "sub/out.txt", "hello")
        assert rel == "sub/out.txt"
        assert read_text(ctx, "sub/out.txt") == "hello"

    def test_read_absolute_artifacts_path(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        target = tmp_path / "abs.txt"
        target.write_text("abs", encoding="utf-8")
        assert read_text(ctx, str(target)) == "abs"

    def test_read_rejects_path_outside_allowed(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        outside = tmp_path.parent / "outside.txt"
        outside.write_text("nope", encoding="utf-8")
        try:
            read_text(ctx, str(outside))
        except ValueError as e:
            assert "outside allowed directories" in str(e)
        else:
            raise AssertionError("expected ValueError")

    def test_read_extra_roots(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        extra = tmp_path / "extra"
        extra.mkdir()
        target = extra / "data.txt"
        target.write_text("extra-data", encoding="utf-8")
        assert read_text(ctx, str(target), extra_roots=(extra,)) == "extra-data"


class TestUtcNowIso:
    def test_returns_iso_string(self) -> None:
        value = utc_now_iso()
        assert isinstance(value, str)
        assert "+00:00" in value


class TestSafeName:
    def test_strips_directory_and_sanitizes(self) -> None:
        assert safe_name("a/b/c.png", fallback="f.png") == "c.png"
        assert safe_name("c d!.png", fallback="f.png") == "c_d_.png"

    def test_empty_falls_back(self) -> None:
        assert safe_name("", fallback="screenshot.png") == "screenshot.png"
```

- [ ] **Step 3: 运行测试,验证失败(红)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_common.py -q`
Expected: FAIL at collection, key line:

```
ModuleNotFoundError: No module named 'plugins.common'
```

---

## Task 2: 实现 `plugins/common/plugin.py`

**Files:**
- Create: `plugins/common/plugin.py`

- [ ] **Step 1: 创建文件(全文)**

```python
# @file /plugins/common/plugin.py
# @brief Plugin 抽象基类:声明式元信息 + 统一注册(替代 hooks.py 样板)
# @create 2026-08-10

from __future__ import annotations

from typing import Any

from app.core.registry import ActionHandler, CheckHandler, Registry


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

> 说明:actions/checks 的 handler 必须是**模块级函数或 `@staticmethod`**(类体内无法引用实例方法);迁移时实例方法一律改为模块级函数。

---

## Task 3: 实现 `plugins/common/helpers.py`

**Files:**
- Create: `plugins/common/helpers.py`

- [ ] **Step 1: 创建文件(全文)**

```python
# @file /plugins/common/helpers.py
# @brief 插件共享工具函数(从 desktop_checkin/zhihu_digest/ai_deepseek 去重而来)
# @create 2026-08-10

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_truthy(v: Any) -> bool:
    """布尔化判定:None/False 为假;字符串按 {1,true,yes,y,on} 判定"""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def dry_run_enabled(ctx: ActionContext, params: dict[str, Any], env_var: str) -> bool:
    """统一 dry_run 判定:params.dry_run > ctx.vars.dry_run > 环境变量 env_var"""
    if is_truthy(params.get("dry_run")):
        return True
    if is_truthy(ctx.vars.get("dry_run")):
        return True
    return is_truthy(os.getenv(env_var))


def read_text(ctx: ActionContext, path: str, extra_roots: tuple[Path, ...] = ()) -> str:
    """安全路径读取(防穿越):仅允许 artifacts 目录、仓库根目录与 extra_roots 内"""
    p = Path(path)
    if not p.is_absolute():
        p = ctx.artifacts_dir / p
    p = p.resolve()
    allowed = {ctx.artifacts_dir.resolve(), _repo_root().resolve(), *extra_roots}
    if not any(p == base or base in p.parents for base in allowed):
        raise ValueError(f"path outside allowed directories: {path}")
    return p.read_text(encoding="utf-8")


def write_text(ctx: ActionContext, rel_path: str, text: str) -> str:
    """写入 artifacts 目录(自动创建父目录),返回相对路径"""
    out_path = ctx.artifacts_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return rel_path


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def safe_name(name: str, fallback: str) -> str:
    """文件名净化:取 basename 并将非法字符替换为下划线,空结果回退到 fallback"""
    n = Path(name).name
    n = re.sub(r"[^a-zA-Z0-9._-]+", "_", n)
    return n or fallback
```

---

## Task 4: 实现 `plugins/common/__init__.py` 并验证测试通过(TDD 绿)

**Files:**
- Create: `plugins/common/__init__.py`

- [ ] **Step 1: 创建文件(全文)**

```python
# @file /plugins/common/__init__.py
# @brief 插件共享代码:导出 Plugin 基类与 helpers(不注册进 plugins.yaml)
# @create 2026-08-10

from plugins.common.helpers import (
    dry_run_enabled,
    is_truthy,
    read_text,
    safe_name,
    utc_now_iso,
    write_text,
)
from plugins.common.plugin import Plugin

__all__ = [
    "Plugin",
    "dry_run_enabled",
    "is_truthy",
    "read_text",
    "safe_name",
    "utc_now_iso",
    "write_text",
]
```

- [ ] **Step 2: 运行测试,验证通过(绿)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_common.py -q`
Expected: PASS, key line:

```
16 passed
```

---

## Task 5: 校验 plugins/common 并提交

**Files:**
- Committed: `plugins/common/plugin.py`、`plugins/common/helpers.py`、`plugins/common/__init__.py`、`backend/tests/conftest.py`、`backend/tests/test_plugin_common.py`

- [ ] **Step 1: ruff 检查与格式检查**

Run: `cd backend && .venv/bin/ruff check app tests ../plugins && .venv/bin/ruff format --check app tests ../plugins`
Expected: `All checks passed!` 与 `N files already formatted`(exit code 0)

- [ ] **Step 2: 全量测试确认仍绿(基线 66 + 新增 16)**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 3: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/common backend/tests/conftest.py backend/tests/test_plugin_common.py
git commit -m "refactor(plugins): add common package with Plugin base class and helpers"
```

---

## Task 6: 迁移 dummy 插件

**Files:**
- Modify: `plugins/dummy/backend.py`(全文重写)
- Modify: `plugins/dummy/__init__.py`(过渡双导出)

- [ ] **Step 1: 重写 `plugins/dummy/backend.py`(全文)**

```python
# @file /plugins/dummy/backend.py
# @brief Dummy 插件：回传用户输入信息（测试用）
# @create 2026-02-21 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _echo(ctx: ActionContext, params: dict[str, Any]) -> Any:
    return {
        "input": ctx.input,
        "message": params.get("message"),
        "vars": ctx.vars,
    }


class DummyPlugin(Plugin):
    """Dummy 插件：回传用户输入信息（测试用）"""

    name = "dummy"
    version = "0.1.0"
    actions = {
        "dummy.echo": _echo,
    }
    checks = {}


PLUGIN = DummyPlugin
```

- [ ] **Step 2: 更新 `plugins/dummy/__init__.py`(过渡期双导出,全文)**

```python
# @file /plugins/dummy/__init__.py
# @brief Dummy 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.dummy.backend import PLUGIN
from plugins.dummy.hooks import register

__all__ = ["PLUGIN", "register"]
```

- [ ] **Step 3: 验证 dummy 可加载且全量测试通过**

Run: `cd backend && .venv/bin/python -c "
from app.runtime import get_registry
r = get_registry()
names = {p.name for p in r.list_plugins()}
assert 'dummy' in names, r.list_plugin_errors()
print('dummy loaded OK')"`
Expected: `dummy loaded OK`

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/dummy/backend.py plugins/dummy/__init__.py
git commit -m "refactor(plugins): migrate dummy plugin to Plugin base class"
```

---

## Task 7: 迁移 desktop_checkin 插件

**Files:**
- Modify: `plugins/desktop_checkin/backend.py`(全文重写)
- Modify: `plugins/desktop_checkin/__init__.py`(过渡双导出)

- [ ] **Step 1: 重写 `plugins/desktop_checkin/backend.py`(全文)**

```python
# @file /plugins/desktop_checkin/backend.py
# @brief 桌面自动打卡插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext
from plugins.common.helpers import dry_run_enabled, is_truthy, safe_name
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_DESKTOP_DRY_RUN"


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / path).resolve()


def _activate_window(ctx: ActionContext, params: dict[str, Any]) -> Any:
    title = str(params.get("title", ""))
    if not title:
        raise ValueError("title is required")

    timeout_seconds = float(params.get("timeout_seconds", 0))
    use_regex = is_truthy(params.get("regex"))
    focus = is_truthy(params.get("focus", True))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "activated": True,
            "title": title,
            "regex": use_regex,
            "focus": focus,
            "dry_run": True,
        }

    try:
        import pygetwindow as gw
    except Exception as e:
        raise RuntimeError(f"pygetwindow unavailable: {e}") from e

    deadline = time.time() + max(0.0, timeout_seconds)
    last_titles: list[str] = []
    while True:
        try:
            windows = gw.getAllWindows()
        except Exception:
            windows = []

        match = None
        if use_regex:
            pattern = re.compile(title)
            for w in windows:
                t = getattr(w, "title", "") or ""
                if pattern.search(t):
                    match = w
                    break
        else:
            for w in windows:
                t = getattr(w, "title", "") or ""
                if title in t:
                    match = w
                    break

        last_titles = [getattr(w, "title", "") or "" for w in windows]
        if match is not None:
            if focus:
                try:
                    match.activate()
                except Exception:
                    pass
            return {
                "activated": True,
                "title": getattr(match, "title", "") or "",
                "dry_run": False,
            }

        if time.time() >= deadline:
            return {
                "activated": False,
                "title": title,
                "dry_run": False,
                "seen_titles": last_titles[:50],
            }
        time.sleep(0.2)


def _click(ctx: ActionContext, params: dict[str, Any]) -> Any:
    x = int(params["x"])
    y = int(params["y"])
    button = str(params.get("button", "left"))
    clicks = int(params.get("clicks", 1))
    interval = float(params.get("interval", 0))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "clicked": True,
            "x": x,
            "y": y,
            "button": button,
            "clicks": clicks,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    return {
        "clicked": True,
        "x": x,
        "y": y,
        "button": button,
        "clicks": clicks,
        "dry_run": False,
    }


def _double_click(ctx: ActionContext, params: dict[str, Any]) -> Any:
    params = dict(params)
    params["clicks"] = 2
    return _click(ctx, params)


def _drag(ctx: ActionContext, params: dict[str, Any]) -> Any:
    from_x = int(params["from_x"])
    from_y = int(params["from_y"])
    to_x = int(params["to_x"])
    to_y = int(params["to_y"])
    duration = float(params.get("duration", 0))
    button = str(params.get("button", "left"))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "dragged": True,
            "from": {"x": from_x, "y": from_y},
            "to": {"x": to_x, "y": to_y},
            "duration": duration,
            "button": button,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.moveTo(from_x, from_y)
    pyautogui.dragTo(to_x, to_y, duration=duration, button=button)
    return {
        "dragged": True,
        "from": {"x": from_x, "y": from_y},
        "to": {"x": to_x, "y": to_y},
        "duration": duration,
        "button": button,
        "dry_run": False,
    }


def _type_text(ctx: ActionContext, params: dict[str, Any]) -> Any:
    text = str(params.get("text", ""))
    interval = float(params.get("interval", 0))
    secret = is_truthy(params.get("secret"))

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {
            "typed": True,
            "length": len(text),
            "secret": secret,
            "dry_run": True,
        }

    import pyautogui

    pyautogui.typewrite(text, interval=interval)
    if secret:
        return {
            "typed": True,
            "length": len(text),
            "secret": True,
            "dry_run": False,
        }
    return {"typed": True, "text": text, "secret": False, "dry_run": False}


def _hotkey(ctx: ActionContext, params: dict[str, Any]) -> Any:
    keys = params.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a non-empty list")
    keys = [str(k) for k in keys]

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {"sent": True, "keys": keys, "dry_run": True}

    import pyautogui

    pyautogui.hotkey(*keys)
    return {"sent": True, "keys": keys, "dry_run": False}


def _wait(ctx: ActionContext, params: dict[str, Any]) -> Any:
    seconds = float(params.get("seconds", 0))
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    dry_run = dry_run_enabled(ctx, params, _DRY_RUN_ENV)
    if not dry_run:
        time.sleep(seconds)
    return {"waited_seconds": seconds, "dry_run": dry_run}


def _screenshot(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = safe_name(
        str(params.get("name", "screenshot.png")), fallback="screenshot.png"
    )
    region = params.get("region")
    fmt = str(params.get("format", "png")).lower()
    if fmt != "png":
        raise ValueError("only png is supported")

    out_dir = ctx.artifacts_dir / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        try:
            from PIL import Image

            Image.new("RGB", (1, 1), color=(0, 0, 0)).save(out_path, format="PNG")
        except Exception:
            out_path.write_bytes(b"")
        return {
            "saved": True,
            "path": str(out_path.relative_to(ctx.artifacts_dir)),
            "dry_run": True,
        }

    import pyautogui

    if region is not None:
        if not isinstance(region, list) or len(region) != 4:
            raise ValueError("region must be [left, top, width, height]")
        region_tuple = (
            int(region[0]),
            int(region[1]),
            int(region[2]),
            int(region[3]),
        )
    else:
        region_tuple = None

    img = pyautogui.screenshot(region=region_tuple)
    img.save(out_path)
    return {
        "saved": True,
        "path": str(out_path.relative_to(ctx.artifacts_dir)),
        "dry_run": False,
    }


def _image_exists(ctx: CheckContext, params: dict[str, Any]) -> bool:
    template_path = params.get("template_path")
    if template_path is None:
        raise ValueError("template_path is required")
    timeout_seconds = float(params.get("timeout_seconds", 0))
    confidence = params.get("confidence")

    deadline = time.time() + max(0.0, timeout_seconds)
    import pyautogui

    template = _resolve_path(str(template_path))
    while True:
        try:
            if confidence is None:
                found = pyautogui.locateOnScreen(str(template))
            else:
                found = pyautogui.locateOnScreen(
                    str(template), confidence=float(confidence)
                )
        except Exception:
            found = None
        if found is not None:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.2)


def _window_title_contains(ctx: CheckContext, params: dict[str, Any]) -> bool:
    needle = str(params.get("needle", ""))
    if not needle:
        raise ValueError("needle is required")
    try:
        import pygetwindow as gw
    except Exception:
        return False
    try:
        w = gw.getActiveWindow()
    except Exception:
        w = None
    title = getattr(w, "title", "") if w is not None else ""
    return needle in (title or "")


class DesktopCheckinPlugin(Plugin):
    """桌面自动打卡插件"""

    name = "desktop-checkin"
    version = "0.1.0"
    actions = {
        "desktop.activate_window": _activate_window,
        "desktop.click": _click,
        "desktop.double_click": _double_click,
        "desktop.drag": _drag,
        "desktop.type_text": _type_text,
        "desktop.hotkey": _hotkey,
        "desktop.wait": _wait,
        "desktop.screenshot": _screenshot,
    }
    checks = {
        "desktop.image_exists": _image_exists,
        "desktop.window_title_contains": _window_title_contains,
    }


PLUGIN = DesktopCheckinPlugin
```

- [ ] **Step 2: 更新 `plugins/desktop_checkin/__init__.py`(过渡期双导出,全文)**

```python
# @file /plugins/desktop_checkin/__init__.py
# @brief 桌面打卡插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.desktop_checkin.backend import PLUGIN
from plugins.desktop_checkin.hooks import register

__all__ = ["PLUGIN", "register"]
```

- [ ] **Step 3: 验证 desktop_checkin 可加载且全量测试通过**

Run: `cd backend && .venv/bin/python -c "
from app.runtime import get_registry
r = get_registry()
names = {p.name for p in r.list_plugins()}
assert 'desktop-checkin' in names, r.list_plugin_errors()
print('desktop_checkin loaded OK')"`
Expected: `desktop_checkin loaded OK`

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/desktop_checkin/backend.py plugins/desktop_checkin/__init__.py
git commit -m "refactor(plugins): migrate desktop_checkin plugin to Plugin base class"
```

---

## Task 8: 迁移 zhihu_digest 插件

**Files:**
- Modify: `plugins/zhihu_digest/backend.py`(全文重写)
- Modify: `plugins/zhihu_digest/__init__.py`(过渡双导出)

- [ ] **Step 1: 重写 `plugins/zhihu_digest/backend.py`(全文)**

```python
# @file /plugins/zhihu_digest/backend.py
# @brief 知乎回答总结插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.core.registry import ActionContext
from plugins.common.helpers import dry_run_enabled, read_text, utc_now_iso, write_text
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_ZHIHU_DRY_RUN"


def _parse_answer_url(url: str) -> tuple[str | None, str | None]:
    m = re.search(r"/question/(\d+)/answer/(\d+)", url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _get_cookie(params: dict[str, Any]) -> str | None:
    cookie = params.get("cookie")
    if isinstance(cookie, str) and cookie.strip():
        if cookie.startswith("env:"):
            return os.getenv(cookie[4:]) or None
        return cookie

    env_name = params.get("cookie_env")
    if isinstance(env_name, str) and env_name.strip():
        return os.getenv(env_name) or None

    return os.getenv("ZHIHU_COOKIE") or None


def _fetch_answer(ctx: ActionContext, params: dict[str, Any]) -> Any:
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url is required")

    question_id, answer_id = _parse_answer_url(url)
    if question_id is None or answer_id is None:
        raise ValueError("unsupported zhihu answer url")

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        answer_text = '点赞后弹出来的"已赞同"可以上下拖动。'
        rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", answer_text)
        return {
            "question_id": question_id,
            "answer_id": answer_id,
            "question_title": None,
            "answer_text_path": rel,
            "source_url": url,
            "fetched_at": utc_now_iso(),
            "dry_run": True,
        }

    mode = str(params.get("mode", "auto")).lower()
    timeout_seconds = float(params.get("timeout_seconds", 30))
    cookie = _get_cookie(params)

    if mode in {"auto", "playwright"}:
        return _fetch_answer_playwright(
            ctx=ctx,
            url=url,
            question_id=question_id,
            answer_id=answer_id,
            timeout_seconds=timeout_seconds,
            cookie=cookie,
        )
    raise ValueError(f"unsupported mode: {mode}")


def _fetch_answer_playwright(
    *,
    ctx: ActionContext,
    url: str,
    question_id: str,
    answer_id: str,
    timeout_seconds: float,
    cookie: str | None,
) -> Any:
    # 优先用 answer_id 定位目标回答的选择器,失败时回退到通用选择器
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(f"playwright unavailable: {e}") from e

    t0 = time.time()
    browser = None
    context = None
    try:
        p = sync_playwright().__enter__()
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if cookie:
            context.set_extra_http_headers({"Cookie": cookie})
        page = context.new_page()
        page.goto(
            url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000)
        )

        selectors = [
            f'div[data-aid="{answer_id}"] div.RichContent-inner',
            f'div[data-aid="{answer_id}"] div.RichContent',
            "div.RichContent-inner",
            "div.RichContent",
            "article",
        ]
        text = ""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(timeout=int(timeout_seconds * 1000))
                text = loc.inner_text().strip()
                if text:
                    break
            except Exception:
                continue

        title = None
        try:
            title = (
                page.locator("h1.QuestionHeader-title").first.inner_text().strip()
            )
        except Exception:
            title = None
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()

    if not text:
        raise RuntimeError("failed to extract answer text")

    rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", text)
    return {
        "question_id": question_id,
        "answer_id": answer_id,
        "question_title": title,
        "answer_text_path": rel,
        "source_url": url,
        "fetched_at": utc_now_iso(),
        "duration_ms": int((time.time() - t0) * 1000),
        "dry_run": False,
    }


def _post_answer_draft(ctx: ActionContext, params: dict[str, Any]) -> Any:
    content_md = params.get("content_md")
    if content_md is None:
        raw_input = params.get("input", None)
        if raw_input is None:
            raw_input = ctx.input
        if isinstance(raw_input, dict) and "summary_path" in raw_input:
            content_md = read_text(ctx, str(raw_input["summary_path"]))
        elif isinstance(raw_input, str):
            content_md = raw_input
        else:
            content_md = ""

    content_md = str(content_md)
    if not content_md.strip():
        raise ValueError("content_md is empty")

    question_url = str(params.get("question_url", "")).strip()
    if not question_url:
        question_url = str(params.get("url", "")).strip()
    if not question_url:
        raise ValueError("question_url is required")

    rel = write_text(ctx, "zhihu/post_content.md", content_md)

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        return {"attempted": False, "saved_path": rel, "dry_run": True}

    cookie = _get_cookie(params)
    if not cookie:
        return {
            "attempted": False,
            "saved_path": rel,
            "dry_run": False,
            "error": "missing ZHIHU_COOKIE",
        }

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {
            "attempted": False,
            "saved_path": rel,
            "dry_run": False,
            "error": f"playwright unavailable: {e}",
        }

    timeout_seconds = float(params.get("timeout_seconds", 60.0))
    attempted = False
    error: str | None = None
    browser = None
    context = None
    try:
        p = sync_playwright().__enter__()
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.set_extra_http_headers({"Cookie": cookie})
        page = context.new_page()
        page.goto(
            question_url,
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        attempted = True
        try:
            page.keyboard.insert_text(content_md[:5000])
        except Exception:
            pass
    except Exception as e:
        error = str(e)
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()

    return {
        "attempted": attempted,
        "saved_path": rel,
        "dry_run": False,
        "error": error,
    }


class ZhihuDigestPlugin(Plugin):
    """知乎回答总结插件"""

    name = "zhihu-digest"
    version = "0.1.0"
    actions = {
        "zhihu.fetch_answer": _fetch_answer,
        "zhihu.post_answer_draft": _post_answer_draft,
    }
    checks = {}


PLUGIN = ZhihuDigestPlugin
```

- [ ] **Step 2: 更新 `plugins/zhihu_digest/__init__.py`(过渡期双导出,全文)**

```python
# @file /plugins/zhihu_digest/__init__.py
# @brief 知乎摘要插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.zhihu_digest.backend import PLUGIN
from plugins.zhihu_digest.hooks import register

__all__ = ["PLUGIN", "register"]
```

- [ ] **Step 3: 验证 zhihu_digest 可加载且全量测试通过**

Run: `cd backend && .venv/bin/python -c "
from app.runtime import get_registry
r = get_registry()
names = {p.name for p in r.list_plugins()}
assert 'zhihu-digest' in names, r.list_plugin_errors()
print('zhihu_digest loaded OK')"`
Expected: `zhihu_digest loaded OK`

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/zhihu_digest/backend.py plugins/zhihu_digest/__init__.py
git commit -m "refactor(plugins): migrate zhihu_digest plugin to Plugin base class"
```

---

## Task 9: 迁移 ai_deepseek 插件

**Files:**
- Modify: `plugins/ai_deepseek/backend.py`(全文重写)
- Modify: `plugins/ai_deepseek/__init__.py`(过渡双导出)

- [ ] **Step 1: 重写 `plugins/ai_deepseek/backend.py`(全文)**

```python
# @file /plugins/ai_deepseek/backend.py
# @brief DeepSeek AI 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
from app.core.registry import ActionContext
from plugins.common.helpers import dry_run_enabled, read_text, write_text
from plugins.common.plugin import Plugin

_DRY_RUN_ENV = "AUTOFLOW_AI_DRY_RUN"


def _get_deepseek_api_key(params: dict[str, Any]) -> str:
    key_ref = params.get("api_key")
    if isinstance(key_ref, str) and key_ref.strip():
        if key_ref.startswith("env:"):
            k = os.getenv(key_ref[4:])
            if k:
                return k
        return key_ref
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key
    raise RuntimeError("missing DEEPSEEK_API_KEY")


@dataclass(frozen=True)
class DeepSeekResult:
    content: str
    raw: dict[str, Any]


class DeepSeekClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def chat_completion(
        self,
        *,
        api_key: str,
        input: str,
        system_prompt: str | None = None,
        model: str = "deepseek-chat",
        temperature: float | None = None,
        max_tokens: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> DeepSeekResult:
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{self._base_url}/v1/chat/completions"

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input})

        payload: dict[str, Any] = {"model": model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        client = http_client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"deepseek request failed: {e}") from e
        finally:
            if http_client is None:
                client.close()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"deepseek response parse failed: {e}") from e
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("deepseek returned empty content")
        return DeepSeekResult(content=content, raw=data)


def _deepseek_summarize(ctx: ActionContext, params: dict[str, Any]) -> Any:
    model = str(params.get("model", "deepseek-chat"))
    system_prompt = params.get("system_prompt")
    temperature = params.get("temperature")
    max_tokens = params.get("max_tokens")

    raw_input = params.get("input", None)
    if raw_input is None:
        raw_input = ctx.input

    if isinstance(raw_input, dict) and "answer_text_path" in raw_input:
        input_text = read_text(ctx, str(raw_input["answer_text_path"]))
    elif isinstance(raw_input, dict) and "path" in raw_input:
        input_text = read_text(ctx, str(raw_input["path"]))
    elif isinstance(raw_input, str):
        input_text = raw_input
    elif raw_input is None:
        input_text = ""
    else:
        input_text = str(raw_input)

    if not input_text.strip():
        raise ValueError("input is empty")

    prompt_rel = write_text(ctx, "ai/prompt.txt", input_text)

    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        summary = "（dry_run）示例总结：要点已整理。"
        out_rel = write_text(ctx, "ai/summary.md", summary)
        return {
            "summary_path": out_rel,
            "prompt_path": prompt_rel,
            "dry_run": True,
            "provider": "deepseek",
        }

    api_key = _get_deepseek_api_key(params)
    client = DeepSeekClient(
        base_url=str(params.get("base_url", "https://api.deepseek.com")),
        timeout_seconds=float(params.get("timeout_seconds", 60.0)),
    )
    result = client.chat_completion(
        api_key=api_key,
        input=input_text,
        system_prompt=str(system_prompt) if system_prompt is not None else None,
        model=model,
        temperature=float(temperature) if temperature is not None else None,
        max_tokens=int(max_tokens) if max_tokens is not None else None,
    )

    out_rel = write_text(ctx, "ai/summary.md", result.content)
    return {
        "summary_path": out_rel,
        "prompt_path": prompt_rel,
        "model": model,
        "dry_run": False,
        "provider": "deepseek",
    }


class AIDeepSeekPlugin(Plugin):
    """DeepSeek AI 插件"""

    name = "ai-deepseek"
    version = "0.1.0"
    actions = {
        "ai.deepseek_summarize": _deepseek_summarize,
    }
    checks = {}


PLUGIN = AIDeepSeekPlugin
```

- [ ] **Step 2: 更新 `plugins/ai_deepseek/__init__.py`(过渡期双导出,全文)**

```python
# @file /plugins/ai_deepseek/__init__.py
# @brief AI DeepSeek 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.ai_deepseek.backend import PLUGIN
from plugins.ai_deepseek.hooks import register

__all__ = ["PLUGIN", "register"]
```

- [ ] **Step 3: 验证 ai_deepseek 可加载且全量测试通过**

Run: `cd backend && .venv/bin/python -c "
from app.runtime import get_registry
r = get_registry()
names = {p.name for p in r.list_plugins()}
assert 'ai-deepseek' in names, r.list_plugin_errors()
print('ai_deepseek loaded OK')"`
Expected: `ai_deepseek loaded OK`

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/ai_deepseek/backend.py plugins/ai_deepseek/__init__.py
git commit -m "refactor(plugins): migrate ai_deepseek plugin to Plugin base class"
```

---

## Task 10: 迁移 openclaw 插件(config 经构造注入)

**Files:**
- Modify: `plugins/openclaw/backend.py`(全文重写)
- Modify: `plugins/openclaw/__init__.py`(过渡双导出)

> 设计说明:handlers 必须为模块级函数(不能引用实例方法),因此 `__init__` 将 config.yaml 的 defaults/secrets 写入模块级 `_DEFAULTS`/`_SECRETS` 供 handlers 读取。插件在进程启动时仅加载一次(`get_registry` 为 `@lru_cache` 单例),该方案安全。`openclaw_plugin/` 子模块(JS)不动。

- [ ] **Step 1: 重写 `plugins/openclaw/backend.py`(全文)**

```python
# @file /plugins/openclaw/backend.py
# @brief OpenClaw 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(config 经构造注入,写入模块级供 handlers 读取)

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.registry import ActionContext, CheckContext
from plugins.common.plugin import Plugin

logger = logging.getLogger(__name__)

# 由 OpenClawPlugin.__init__ 注入(config.yaml 的 defaults/secrets);
# 插件在进程启动时仅加载一次(get_registry 为 lru_cache 单例),模块级变量即足够。
_DEFAULTS: dict[str, Any] = {}
_SECRETS: dict[str, Any] = {}


def _http_request(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    method = params.get("method", "GET").upper()
    url = params.get("url")
    headers = params.get("headers", {})
    body = params.get("body")
    timeout = params.get("timeout") or _DEFAULTS.get("http_timeout", 30)

    if not url:
        return {
            "error": "url is required",
            "status_code": None,
            "headers": None,
            "body": None,
        }

    try:
        req = Request(url, method=method)
        for key, value in headers.items():
            req.add_header(key, value)

        if body:
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
                req.add_header("Content-Type", "application/json")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            req.data = body

        with urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            try:
                response_body = json.loads(response_body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

            return {
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": response_body,
            }
    except HTTPError as e:
        return {
            "status_code": e.code,
            "headers": dict(e.headers) if e.headers else {},
            "body": e.read().decode("utf-8") if e.fp else None,
            "error": str(e),
            "error_type": "http_error",
        }
    except URLError as e:
        return {
            "status_code": None,
            "headers": None,
            "body": None,
            "error": str(e.reason),
            "error_type": "network_error",
        }
    except Exception as e:
        return {
            "status_code": None,
            "headers": None,
            "body": None,
            "error": str(e),
            "error_type": "unknown_error",
        }


def _exec_command(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a shell command with optional safety controls.

    Security note: When safe_mode is False, commands run with shell=True,
    which is vulnerable to command injection. Only disable safe_mode when
    you fully trust the command source.
    """
    command = params.get("command")
    args = params.get("args")  # 可选参数列表
    cwd = params.get("cwd")

    # Convert timeout to float; guard against YAML string values
    timeout_raw = params.get("timeout") or _DEFAULTS.get("exec_timeout", 60)
    try:
        timeout = float(timeout_raw)
    except (TypeError, ValueError):
        timeout = 60.0

    safe_mode = params.get("safe_mode", _DEFAULTS.get("safe_mode", True))
    allowed_commands = _DEFAULTS.get("allowed_commands", [])

    if not safe_mode:
        logger.warning(
            "exec_command running with safe_mode=False — "
            "command injection risk is present"
        )

    if not command:
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": "command is required",
            "error": "command is required",
        }

    # 白名单校验（若配置了 allowed_commands）
    if allowed_commands:
        matched = any(re.match(pattern, command) for pattern in allowed_commands)
        if not matched:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"command not allowed: {command}",
                "error": "command_not_allowed",
            }

    # 构建执行参数
    # Windows 上内建命令（echo/dir等）需要 shell=True，
    # safe_mode 下仍用 shlex 解析但保留 shell
    _is_windows = sys.platform == "win32"
    if args is not None:
        # 显式传了 args，使用列表模式
        cmd = [command] + list(args)
        use_shell = _is_windows  # Windows 需要 shell=True 才能找到内建命令
    elif safe_mode:
        # safe_mode：用 shlex.split 解析参数，防止注入；Windows 下仍需 shell
        cmd = shlex.split(command, posix=not _is_windows)
        use_shell = _is_windows
    else:
        # 显式关闭 safe_mode 时才使用 shell=True
        cmd = command
        use_shell = True

    try:
        result = subprocess.run(
            cmd,
            shell=use_shell,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "error": "timeout",
            "error_type": "timeout",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "error": str(e),
            "error_type": "unknown_error",
        }


def _knowflow_record(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    default_base_url = (
        _SECRETS.get("knowflow_base_url")
        or os.environ.get("KNOWFLOW_BASE_URL")
        or "http://localhost:3000"
    )
    base_url = params.get("base_url") or default_base_url
    name = params.get("name")
    project_id = params.get("project_id")
    archive_type = params.get("archive_type", "document")
    summary = params.get("summary", "")
    content = params.get("content", "")
    agent_source = params.get("agent_source", "autoflow")

    if not name:
        return {
            "item_id": None,
            "name": None,
            "success": False,
            "error": "name is required",
        }
    if not project_id:
        return {
            "item_id": None,
            "name": name,
            "success": False,
            "error": "project_id is required",
        }

    try:
        create_url = f"{base_url}/api/v1/item"
        payload = {
            "name": name,
            "projectId": project_id,
            "archiveType": archive_type,
            "summary": summary,
            "content": content,
        }

        if agent_source:
            payload["agent"] = agent_source

        data = json.dumps(payload).encode("utf-8")
        req = Request(create_url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=30) as response:
            create_result = json.loads(response.read().decode("utf-8"))
            item_id = create_result.get("id") or create_result.get("_id")
            if not item_id:
                return {
                    "item_id": None,
                    "name": name,
                    "success": False,
                    "error": "Failed to get item_id from response",
                }

        update_url = (
            f"{base_url}/api/v1/plugins/knowflow_openclaw/items/{item_id}/openclaw"
        )
        update_payload = {"agent": agent_source, "source": "autoflow"}
        update_data = json.dumps(update_payload).encode("utf-8")

        update_req = Request(update_url, data=update_data, method="PUT")
        update_req.add_header("Content-Type", "application/json")

        update_warning = None
        try:
            with urlopen(update_req, timeout=30) as response:
                response.read()
        except HTTPError as e:
            update_warning = f"openclaw attribute update failed: HTTP {e.code}"
        except Exception as e:
            update_warning = f"openclaw attribute update failed: {e}"

        result = {"item_id": item_id, "name": name, "success": True}
        if update_warning:
            result["warning"] = update_warning
        return result

    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {
            "item_id": None,
            "name": name,
            "success": False,
            "error": f"HTTP {e.code}: {error_body}",
            "error_type": "http_error",
        }
    except URLError as e:
        return {
            "item_id": None,
            "name": name,
            "success": False,
            "error": str(e.reason),
            "error_type": "network_error",
        }
    except Exception as e:
        return {
            "item_id": None,
            "name": name,
            "success": False,
            "error": str(e),
            "error_type": "unknown_error",
        }


def _status_code_ok(ctx: CheckContext, params: dict[str, Any]) -> bool:
    expected = params.get("expected", 200)
    action_output = ctx.action_output

    if not action_output:
        return False

    status_code = action_output.get("status_code")
    return status_code == expected


def _exit_code_zero(ctx: CheckContext, params: dict[str, Any]) -> bool:
    action_output = ctx.action_output

    if not action_output:
        return False

    exit_code = action_output.get("exit_code")
    return exit_code == 0


class OpenClawPlugin(Plugin):
    """OpenClaw 插件:HTTP 请求、命令执行、KnowFlow 记录"""

    name = "openclaw"
    version = "0.1.0"
    actions = {
        "openclaw.http_request": _http_request,
        "openclaw.exec": _exec_command,
        "openclaw.knowflow_record": _knowflow_record,
    }
    checks = {
        "openclaw.status_code_ok": _status_code_ok,
        "openclaw.exit_code_zero": _exit_code_zero,
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        _DEFAULTS.clear()
        _DEFAULTS.update(self.config.get("defaults", {}))
        _SECRETS.clear()
        _SECRETS.update(self.config.get("secrets", {}))


PLUGIN = OpenClawPlugin
```

- [ ] **Step 2: 更新 `plugins/openclaw/__init__.py`(过渡期双导出,全文)**

```python
# @file /plugins/openclaw/__init__.py
# @brief OpenClaw 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(register 为过渡期保留,Task 15 移除)

from plugins.openclaw.backend import PLUGIN
from plugins.openclaw.hooks import register

__all__ = ["PLUGIN", "register"]
```

- [ ] **Step 3: 验证 openclaw 可加载(含 config 注入)且全量测试通过**

Run: `cd backend && .venv/bin/python -c "
from app.runtime import get_registry
r = get_registry()
names = {p.name for p in r.list_plugins()}
assert 'openclaw' in names, r.list_plugin_errors()
from plugins.openclaw.backend import _DEFAULTS
assert _DEFAULTS.get('safe_mode') is True, _DEFAULTS
print('openclaw loaded OK, safe_mode default =', _DEFAULTS.get('safe_mode'))"`
Expected: `openclaw loaded OK, safe_mode default = True`

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
82 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/openclaw/backend.py plugins/openclaw/__init__.py
git commit -m "refactor(plugins): migrate openclaw plugin to Plugin base class"
```

---

## Task 11: 迁移 examples/hello_world.py

**Files:**
- Modify: `plugins/examples/hello_world.py`(全文重写)

> 说明:examples 插件不在 `plugins.yaml` 中,loader 不会加载,可直接删除 register 函数。

- [ ] **Step 1: 重写 `plugins/examples/hello_world.py`(全文)**

```python
# @file /plugins/examples/hello_world.py
# @brief 示例插件：注册 core.hello action
# @create 2026-08-09
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _hello(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = params.get("name", "World")
    return {"message": f"Hello, {name} from AutoFlow!"}


class HelloWorldPlugin(Plugin):
    """示例插件：注册 core.hello action"""

    name = "hello-world"
    version = "1.0.0"
    actions = {
        "core.hello": _hello,
    }
    checks = {}


PLUGIN = HelloWorldPlugin
```

- [ ] **Step 2: 验证模块可导入且 PLUGIN 为 Plugin 子类**

> 说明:在 `backend/` 下运行(cwd 使 `app` 可导入),并显式把仓库根目录加入 `sys.path` 使 `plugins.*` 可导入。

Run: `cd backend && .venv/bin/python -c "
import sys
sys.path.insert(0, '..')
from plugins.examples.hello_world import PLUGIN
from plugins.common.plugin import Plugin
assert issubclass(PLUGIN, Plugin) and PLUGIN.name == 'hello-world'
print('hello_world OK')"`
Expected: `hello_world OK`

- [ ] **Step 3: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/examples/hello_world.py
git commit -m "refactor(plugins): migrate hello_world example to Plugin base class"
```

---

## Task 12: 迁移 examples/dummy_echo.py

**Files:**
- Modify: `plugins/examples/dummy_echo.py`(全文重写)

- [ ] **Step 1: 重写 `plugins/examples/dummy_echo.py`(全文)**

```python
# @file /plugins/examples/dummy_echo.py
# @brief 示例插件：注册 dummy.echo action,回传用户输入信息
# @create 2026-02-21 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _echo(ctx: ActionContext, params: dict[str, Any]) -> Any:
    return {
        "input": ctx.input,
        "message": params.get("message"),
        "vars": ctx.vars,
    }


class DummyEchoPlugin(Plugin):
    """示例插件：注册 dummy.echo action"""

    name = "dummy-echo"
    version = "0.1.0"
    actions = {
        "dummy.echo": _echo,
    }
    checks = {}


PLUGIN = DummyEchoPlugin
```

- [ ] **Step 2: 验证模块可导入且 PLUGIN 为 Plugin 子类**

Run: `cd backend && .venv/bin/python -c "
import sys
sys.path.insert(0, '..')
from plugins.examples.dummy_echo import PLUGIN
from plugins.common.plugin import Plugin
assert issubclass(PLUGIN, Plugin) and PLUGIN.name == 'dummy-echo'
print('dummy_echo OK')"`
Expected: `dummy_echo OK`

- [ ] **Step 3: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/examples/dummy_echo.py
git commit -m "refactor(plugins): migrate dummy_echo example to Plugin base class"
```

---

## Task 13: 重写 test_plugin_loader.py 适配新协议(先红)

**Files:**
- Modify: `backend/tests/test_plugin_loader.py`(全文重写)

- [ ] **Step 1: 重写 `backend/tests/test_plugin_loader.py`(全文)**

```python
# @file /backend/tests/test_plugin_loader.py
# @brief Tests for plugin_loader: YAML parsing, config loading, PLUGIN (Plugin 子类) 加载
# @create 2026-08-10

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import yaml
from app.core.registry import Registry
from app.runtime.plugin_loader import (
    _load_plugin_config,
    _load_registry_entries,
    load_plugins,
)
from plugins.common.plugin import Plugin


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


class _RecordingPlugin(Plugin):
    """记录构造接收到的 config,便于断言 config 注入。"""

    name = "test-plugin"
    version = "9.9.9"
    actions: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    instances: list["_RecordingPlugin"] = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.received_config = config
        _RecordingPlugin.instances.append(self)


class TestLoadRegistryEntries:
    """Test plugins.yaml parsing."""

    def test_empty_when_no_yaml(self, tmp_path: Path):
        entries = _load_registry_entries(tmp_path)
        assert entries == {}

    def test_parses_enabled_plugins(self, tmp_path: Path):
        _write_yaml(
            tmp_path / "plugins.yaml",
            {
                "plugins": {
                    "dummy": {"enabled": True},
                    "disabled_plugin": {"enabled": False},
                }
            },
        )
        entries = _load_registry_entries(tmp_path)
        assert "dummy" in entries
        assert "disabled_plugin" not in entries

    def test_handles_missing_path_key(self, tmp_path: Path):
        _write_yaml(
            tmp_path / "plugins.yaml",
            {"plugins": {"test_plugin": {"enabled": True}}},
        )
        entries = _load_registry_entries(tmp_path)
        assert "test_plugin" in entries
        # Defaults to plugin key as path
        assert entries["test_plugin"]["path"].name == "test_plugin"


class TestLoadPluginConfig:
    """Test config.yaml loading and secrets resolution."""

    def test_none_when_no_config(self, tmp_path: Path):
        config = _load_plugin_config(tmp_path)
        assert config is None

    def test_loads_defaults_and_secrets(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "secret-123")
        monkeypatch.setenv("TEST_BASE_URL", "http://example.com")

        _write_yaml(
            tmp_path / "config.yaml",
            {
                "defaults": {"timeout": 30, "dry_run": False},
                "secrets": {
                    "api_key": "TEST_API_KEY",
                    "base_url": "TEST_BASE_URL",
                    "missing": "MISSING_VAR",
                },
            },
        )
        config = _load_plugin_config(tmp_path)
        assert config is not None
        assert config["defaults"] == {"timeout": 30, "dry_run": False}
        assert config["secrets"] == {
            "api_key": "secret-123",
            "base_url": "http://example.com",
            "missing": None,
        }

    def test_no_secrets_block(self, tmp_path: Path):
        _write_yaml(tmp_path / "config.yaml", {"defaults": {"x": 1}})
        config = _load_plugin_config(tmp_path)
        assert config is not None
        assert config["defaults"] == {"x": 1}
        assert "secrets" not in config


class TestPluginLoaderIntegration:
    """Integration tests for load_plugins with mocked imports (PLUGIN 协议)。"""

    def _make_plugin_dir(self, tmp_path: Path) -> Path:
        plugin_dir = tmp_path / "plugins" / "test_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
        return plugin_dir

    def _mock_import(self, monkeypatch, plugins_dir: Path, module) -> None:
        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"test_p": {"path": plugins_dir / "test_plugin"}},
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            lambda name: module,
        )

    def test_loads_directory_plugin_with_config(self, monkeypatch, tmp_path: Path):
        """PLUGIN 识别 + config.yaml 解析结果注入构造 + 注册到 registry。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        plugin_dir = self._make_plugin_dir(tmp_path)

        _write_yaml(
            plugin_dir / "config.yaml",
            {"defaults": {"name": "from_config"}, "secrets": {}},
        )

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        assert len(_RecordingPlugin.instances) == 1
        config = _RecordingPlugin.instances[0].received_config
        assert config is not None
        assert config["defaults"] == {"name": "from_config"}

        plugins = registry.list_plugins()
        assert [(p.name, p.version) for p in plugins] == [("test-plugin", "9.9.9")]

    def test_disabled_plugin_not_loaded(self, monkeypatch):
        """Disabled plugins should not trigger module loading."""
        registry = Registry()

        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: Path("/fake/plugins"),
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {},
        )

        import_mock = MagicMock()
        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            import_mock,
        )

        load_plugins(registry)

        # import_module should never be called for empty entries
        import_mock.assert_not_called()

    def test_loads_plugin_passes_none_config_when_missing(
        self, monkeypatch, tmp_path: Path
    ):
        """缺少 config.yaml 时 PLUGIN 构造应收到 config=None。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        self._make_plugin_dir(tmp_path)

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        assert len(_RecordingPlugin.instances) == 1
        assert _RecordingPlugin.instances[0].received_config is None

    def test_module_without_plugin_reports_error(self, monkeypatch, tmp_path: Path):
        """模块未暴露 PLUGIN 时应上报到 registry.add_plugin_error。"""
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        self._make_plugin_dir(tmp_path)

        # spec=[] 使任意属性访问抛 AttributeError,模拟无 PLUGIN 的模块
        mock_module = MagicMock(spec=[])

        self._mock_import(monkeypatch, plugins_dir, mock_module)

        load_plugins(registry)

        errors = registry.list_plugin_errors()
        assert len(errors) == 1
        assert "PLUGIN" in errors[0].error
        assert errors[0].plugin_id == "test_p"
```

- [ ] **Step 2: 运行测试,验证失败(红)——旧 loader 仍走 register 协议**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_loader.py -q`
Expected: FAIL, key lines:

```
FAILED tests/test_plugin_loader.py::TestPluginLoaderIntegration::test_loads_directory_plugin_with_config
FAILED tests/test_plugin_loader.py::TestPluginLoaderIntegration::test_loads_plugin_passes_none_config_when_missing
FAILED tests/test_plugin_loader.py::TestPluginLoaderIntegration::test_module_without_plugin_reports_error
... 3 failed, 7 passed in ...
```

---

## Task 14: 切换 plugin_loader 至 PLUGIN 协议(最小调整)

**Files:**
- Modify: `backend/app/runtime/plugin_loader.py`(全文重写)

> 阶段二说明:本任务只做「能加载新 ABI 插件」的最小调整(识别 `PLUGIN`、注入 config、调用 `plugin.register`),错误上报行为不变。loader 的最终收敛(注释、docstring 进一步清理、后续重构)归阶段二。删除 `getattr(module, "register")` 协议即在此完成,不再保留兼容层。

- [ ] **Step 1: 重写 `backend/app/runtime/plugin_loader.py`(全文)**

```python
# @file /backend/app/runtime/plugin_loader.py
# @brief 插件加载器 - runtime 统一加载 plugins.yaml 启用的插件并注册到 Registry
# @create 2026-08-08
# @update 2026-08-10 阶段一:识别 PLUGIN (Plugin 子类) 新 ABI;更深度收敛归阶段二

from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from app.core.registry import Registry
from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)

DEFAULT_PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"


def _plugins_dir() -> Path:
    configured = setting_manager.get("PLUGINS_DIR", "")
    if configured:
        return Path(configured)
    return DEFAULT_PLUGINS_DIR


def _load_registry_entries(plugins_dir: Path) -> dict[str, dict[str, Any]]:
    """读取 plugins.yaml,返回 {plugin_key: {path, enabled}}"""
    registry_path = plugins_dir / "plugins.yaml"
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"读取插件注册表失败: {registry_path} - {e}")
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for key, cfg in data.get("plugins", {}).items():
        if cfg is None:
            continue
        if not cfg.get("enabled", True):
            logger.debug(f"插件 {key} 已禁用,跳过")
            continue

        raw_path = cfg.get("path", key)
        path = Path(raw_path)
        if not path.is_absolute():
            path = (plugins_dir / path).resolve()

        entries[key] = {"path": path}
    return entries


def _load_plugin_config(plugin_dir: Path) -> dict[str, Any] | None:
    """Load and resolve config.yaml from a plugin directory.

    Returns None when no config.yaml is present.
    Resolves the secrets block by looking up each value in the environment.
    """
    config_path = plugin_dir / "config.yaml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load plugin config {config_path}: {e}")
        return None

    secrets = config.get("secrets")
    if isinstance(secrets, dict):
        resolved: dict[str, str | None] = {}
        for key, env_var in secrets.items():
            if isinstance(env_var, str):
                resolved[key] = os.getenv(env_var)
        config["secrets"] = resolved

    return config


def load_plugins(registry: Registry) -> None:
    """加载 plugins.yaml 中启用的插件,识别模块导出的 PLUGIN (Plugin 子类) 完成注册

    插件模块需暴露 PLUGIN = XxxPlugin (Plugin 子类),见 plugins/common/plugin.py。
    单个插件加载失败不会影响其他插件,错误会记录到 registry。
    """
    plugins_dir = _plugins_dir()
    if not plugins_dir.exists():
        logger.warning(f"插件目录不存在: {plugins_dir},跳过插件加载")
        return

    entries = _load_registry_entries(plugins_dir)
    if not entries:
        logger.debug("插件注册表为空,跳过插件加载")
        return

    parent_dir = str(plugins_dir.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # 延迟导入:依赖上面 sys.path 注入仓库根目录后 plugins 包才可导入
    from plugins.common.plugin import Plugin

    for key, entry in entries.items():
        path: Path = entry["path"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"插件路径不存在: {path}")

            if path.is_dir():
                if not (path / "__init__.py").exists():
                    raise FileNotFoundError(f"插件目录 {path} 下未找到 __init__.py")
            elif not path.is_file() or path.suffix != ".py":
                raise ValueError(f"插件路径既不是目录也不是 .py 文件: {path}")

            # 模块名取解析后路径的目录名/文件名,与 plugins.yaml 的 key 解耦
            # For file plugins, compute relative path to support sub-directories
            # e.g. plugins/examples/hello_world.py → plugins.examples.hello_world
            if path.is_dir():
                module_name = path.name
            else:
                rel = path.resolve().relative_to(plugins_dir.resolve())
                # Strip .py suffix and convert path separators to dots
                module_name = (
                    str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
                )
            module = importlib.import_module(f"plugins.{module_name}")

            plugin_cls = getattr(module, "PLUGIN", None)
            if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, Plugin)):
                raise AttributeError(
                    f"插件模块 {module_name} 未暴露 PLUGIN (Plugin 子类)"
                )

            # Load config.yaml if the plugin is a directory
            config = None
            if path.is_dir():
                config = _load_plugin_config(path)

            plugin = plugin_cls(config)
            plugin.register(registry)
            logger.info(f"成功加载插件: {key} ({path})")
        except Exception as e:
            logger.error(f"加载插件 {key} 失败: {e}", exc_info=True)
            registry.add_plugin_error(plugin_id=key, file_path=str(path), error=str(e))
```

- [ ] **Step 2: 运行 loader 测试,验证通过(绿)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_loader.py -q`
Expected: PASS, key line:

```
10 passed
```

- [ ] **Step 3: 运行全量测试(所有插件已双导出 PLUGIN)**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
83 passed
```

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/runtime/plugin_loader.py backend/tests/test_plugin_loader.py
git commit -m "refactor(backend): switch plugin_loader to PLUGIN (Plugin subclass) protocol"
```

---

## Task 15: 删除 hooks.py,__init__ 仅导出 PLUGIN

**Files:**
- Delete: `plugins/dummy/hooks.py`、`plugins/desktop_checkin/hooks.py`、`plugins/zhihu_digest/hooks.py`、`plugins/ai_deepseek/hooks.py`、`plugins/openclaw/hooks.py`
- Modify: 5 个 `plugins/*/__init__.py`(移除 register 导入)

- [ ] **Step 1: 删除 5 个 hooks.py**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
rm plugins/dummy/hooks.py plugins/desktop_checkin/hooks.py plugins/zhihu_digest/hooks.py plugins/ai_deepseek/hooks.py plugins/openclaw/hooks.py
```

- [ ] **Step 2: 更新 5 个 `__init__.py`(仅导出 PLUGIN,全文如下)**

`plugins/dummy/__init__.py`:

```python
# @file /plugins/dummy/__init__.py
# @brief Dummy 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.dummy.backend import PLUGIN

__all__ = ["PLUGIN"]
```

`plugins/desktop_checkin/__init__.py`:

```python
# @file /plugins/desktop_checkin/__init__.py
# @brief 桌面打卡插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.desktop_checkin.backend import PLUGIN

__all__ = ["PLUGIN"]
```

`plugins/zhihu_digest/__init__.py`:

```python
# @file /plugins/zhihu_digest/__init__.py
# @brief 知乎摘要插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.zhihu_digest.backend import PLUGIN

__all__ = ["PLUGIN"]
```

`plugins/ai_deepseek/__init__.py`:

```python
# @file /plugins/ai_deepseek/__init__.py
# @brief AI DeepSeek 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.ai_deepseek.backend import PLUGIN

__all__ = ["PLUGIN"]
```

`plugins/openclaw/__init__.py`:

```python
# @file /plugins/openclaw/__init__.py
# @brief OpenClaw 插件入口
# @create 2026-03-27
# @update 2026-08-10 迁移为 Plugin 基类新 ABI

from plugins.openclaw.backend import PLUGIN

__all__ = ["PLUGIN"]
```

- [ ] **Step 3: 验证 grep 无残留 register 协议**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "def register(registry" plugins/`
Expected: 无输出(exit code 1),`plugins/` 下 `def register(registry` 命中 0

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "hooks import\|from plugins.*hooks" plugins/`
Expected: 无输出(exit code 1)

- [ ] **Step 4: 运行全量测试,验证通过**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
83 passed
```

- [ ] **Step 5: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add -A plugins/
git commit -m "refactor(plugins): remove hooks.py, export PLUGIN only"
```

---

## Task 16: 更新 plugins/index.md 为新 ABI 说明

**Files:**
- Modify: `plugins/index.md`(全文重写)

- [ ] **Step 1: 重写 `plugins/index.md`(全文)**

````markdown
---
title: 插件系统
description: AutoFlow 插件系统文档
keywords: [插件, plugin, 系统, 扩展]
version: "2.0"
---

# AutoFlow 插件系统

本目录包含 AutoFlow 的所有插件。插件是扩展核心引擎功能的 Python 模块。

## 📁 目录结构

```
plugins/
├── plugins.yaml              # 插件注册表（启用/禁用控制）
├── index.md                  # 本文件
├── common/                   # 插件共享代码（Plugin 基类 + helpers,不注册进 plugins.yaml）
│   ├── __init__.py           # 导出 Plugin 与 helpers
│   ├── plugin.py             # Plugin 抽象基类
│   └── helpers.py            # 共享工具函数
│
├── dummy/                    # 示例插件
├── ai_deepseek/              # DeepSeek AI 集成
├── zhihu_digest/             # 知乎摘要
├── desktop_checkin/          # 桌面签到
├── openclaw/                 # OpenClaw 自动化 (含 openclaw_plugin 子模块)
│
└── examples/                 # 插件开发示例
    ├── hello_world.py
    └── dummy_echo.py
```

## 📋 插件标准结构

一个标准的目录插件：

```
my_plugin/
├── __init__.py       # 包入口（导出 PLUGIN）
├── backend.py        # class XxxPlugin(Plugin),actions/checks 以类属性声明
└── config.yaml       # 可选,defaults + secrets(secrets 由 loader 解析为环境变量值)
```

文件插件（如 `examples/*.py`）直接在单文件中定义 Plugin 子类并导出 `PLUGIN`。

## ⚙️ 插件注册表

在 `plugins.yaml` 中控制插件的启用状态：

```yaml
plugins:
  dummy:
    enabled: true
  ai_deepseek:
    enabled: true
  # ...
```

## 🚀 插件加载

AutoFlow 通过 `backend/app/runtime/plugin_loader.py` 统一加载插件：

1. 读取 `plugins/plugins.yaml` 中启用的插件
2. 导入对应模块（目录插件要求包含 `__init__.py`）
3. 识别模块导出的 `PLUGIN`（Plugin 子类），实例化并注入 config
4. 调用 `plugin.register(registry)` 完成注册

插件约定（**唯一**注册入口）：

```python
# plugins/my_plugin/backend.py
from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _my_action(ctx: ActionContext, params: dict) -> dict:
    message = params.get("message", "hello")
    return {"message": message}


class MyPlugin(Plugin):
    name = "my-plugin"
    version = "0.1.0"
    actions = {"my.action": _my_action}
    checks = {}


PLUGIN = MyPlugin
```

- `Plugin` 基类（`plugins/common/plugin.py`）提供声明式 `name/version/actions/checks` 与统一的 `register(registry)`。
- actions/checks 的 handler 必须是模块级函数或 `@staticmethod`（类体内无法引用实例方法）。
- `config` 由 `plugin_loader` 自动从插件目录下的 `config.yaml` 加载并注入构造：`defaults` 原样传入，`secrets` block 会被解析为对应环境变量的值。无 `config.yaml` 时传入 `None`。
- 共享工具函数见 `plugins/common/helpers.py`：`is_truthy`、`dry_run_enabled(ctx, params, env_var)`、`read_text(ctx, path, extra_roots=())`、`write_text(ctx, rel_path, text)`、`utc_now_iso()`、`safe_name(name, fallback)`。
- 单个插件加载失败不影响其他插件，错误会记录到 Registry 的 `list_plugin_errors()`。

## 📖 开发指南

参考 `docs/zh/plugin-dev-guide.md` 了解完整的插件开发指南（完整指南迁移到新 ABI 属阶段四）。
````

- [ ] **Step 2: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add plugins/index.md
git commit -m "docs(plugins): update index.md for new Plugin ABI"
```

---

## Task 17: 最终验收

**Files:**
- 验证全部 spec 第 8 章验收项(无需新代码)

- [ ] **Step 1: grep 验收——plugins/ 下无 register 协议残留**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "def register(registry" plugins/`
Expected: 无输出(exit code 1),命中 0

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rln "hooks.py" plugins/ || true`
Expected: 无文件残留引用(`plugins/` 下已无 hooks.py)

- [ ] **Step 2: ruff 检查**

Run: `cd backend && .venv/bin/ruff check app tests ../plugins && .venv/bin/ruff format --check app tests ../plugins`
Expected: `All checks passed!` 与 `N files already formatted`(exit code 0)

- [ ] **Step 3: 全量 pytest**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
83 passed
```

- [ ] **Step 4: 启动冒烟——/api/v1/plugins 返回 6 插件 + /runs/execute 执行通过**

Run: `cd backend && .venv/bin/python - <<'EOF'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

resp = client.get("/api/v1/plugins")
assert resp.status_code == 200
data = resp.json()
print("plugins:", [p["name"] for p in data["plugins"]])
assert len(data["plugins"]) == 6, data
assert data["errors"] == [], data["errors"]

flow_yaml = """
version: "1"
name: "smoke-dry-run"
steps:
  - id: "echo"
    action:
      type: "dummy.echo"
      params:
        message: "smoke"
""".lstrip()
resp = client.post(
    "/api/v1/runs/execute", json={"flow_yaml": flow_yaml, "vars": {"dry_run": True}}
)
assert resp.status_code == 200
run = resp.json()
print("run status:", run["status"])
assert run["status"] == "success"
print("OK: 6 plugins, smoke run success")
EOF`
Expected: key lines:

```
plugins: ['builtin', 'dummy', 'openclaw', 'ai-deepseek', 'zhihu-digest', 'desktop-checkin']
run status: success
OK: 6 plugins, smoke run success
```

- [ ] **Step 5: 冒烟后检查 git 状态干净(无未提交改动)**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && git status --short`
Expected: 无输出(工作区干净)

---

## 2. 验收汇总(对应 spec 第 3.5 节与第 8 章)

| 验收项 | 验证任务 |
|--------|----------|
| PLUGIN 识别、config 注入、无 PLUGIN 错误上报测试 | Task 13、Task 14(新增 4 个集成用例) |
| 插件无重复样板,grep `def register(registry` 在 plugins/ 下为 0 | Task 15 Step 3、Task 17 Step 1 |
| hooks.py 全部删除 | Task 15 |
| 全部 pytest 通过 | Task 17 Step 3(`83 passed`) |
| `/api/v1/plugins` 返回 6 个插件、`/runs/execute` 冒烟通过 | Task 17 Step 4 |
| 插件目录/文件两种形态模块解析保留 | Task 14(loader 逻辑未改模块名解析) |
| plugins/common 不注册进 plugins.yaml、不被 loader 加载 | Task 14(loader 只遍历 plugins.yaml 条目) |
| openclaw_plugin 子模块(JS)不动 | Task 10(仅改 Python 壳,未触碰子模块) |
