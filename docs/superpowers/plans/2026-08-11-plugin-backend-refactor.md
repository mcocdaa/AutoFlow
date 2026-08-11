# 插件共性层与后端去重优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将插件 handlers 统一为类方法形态,在 Plugin 基类收敛 dry_run/配置取值/错误返回三类重复,并对后端 runner/registry/setting_manager 做纯重构去重。

**Architecture:** 基类提供实例级 `defaults`/`secrets` + `is_dry_run()`/`setting()`/`error_result()` 共性 API,actions/checks 改为 `__init__` 中绑定的实例属性;5 个插件 + 2 个 examples 全部迁移为实例方法。Task 1 采用"类属性兼容合并"过渡(旧插件类属性 actions 复制进实例),保证每个任务结束时 pytest 全绿,Task 8 清理过渡代码。

**Tech Stack:** Python 3.11+、pytest、FastAPI TestClient(端到端)、ruff(pre-commit 含 ruff hook)

**调研依据:** python-patterns.guide(全局可变状态反模式 → 实例级状态)、stevedore(loader 职责不变)、Ansible check mode(dry_run 两级模型)、pydantic-settings(分层取值链)、12-factor(secrets 走 env)、Ansible module 返回契约(统一 dict 返回)

**验证基线(实施前确认):** `PYTHONPATH=backend:. pytest backend/tests plugins -q` 当前 95 passed

---

## Task 1: Plugin 基类增强 + helpers 新增 + 单测

**Files:**
- Modify: `plugins/common/plugin.py`(全文替换)
- Modify: `plugins/common/helpers.py`(新增 resolve_env_value / error_result,保留 dry_run_enabled)
- Modify: `backend/tests/test_plugin_common.py`(适配实例属性 + 新增 3 组测试)

- [ ] **Step 1: 重写 `plugins/common/plugin.py`**

```python
# @file /plugins/common/plugin.py
# @brief Plugin 抽象基类:声明式元信息 + 统一注册 + 配置/dry_run/错误共性 API
# @create 2026-08-10
# @update 2026-08-11 增加实例级 defaults/secrets、is_dry_run/setting/error_result,
#   actions/checks 实例属性化(Task 8 移除类属性兼容合并)

from __future__ import annotations

import os
from typing import Any

from app.core.registry import ActionContext, ActionHandler, CheckHandler, Registry

from plugins.common.helpers import is_truthy, resolve_env_value


class Plugin:
    """插件基类:声明式元信息 + 统一注册 + 配置/dry_run/错误共性 API"""

    name: str
    version: str = "0.1.0"
    dry_run_env: str | None = None
    actions: dict[str, ActionHandler] = {}  # 类属性默认(兼容旧 ABI);Task 8 移除
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))
        self.secrets = dict(self.config.get("secrets", {}))
        # 兼容过渡:复制子类类属性声明(旧 ABI);新 ABI 在子类 __init__ 覆盖为实例绑定方法
        self.actions: dict[str, ActionHandler] = dict(type(self).actions)
        self.checks: dict[str, CheckHandler] = dict(type(self).checks)

    def register(self, registry: Registry) -> None:
        """注册 plugin 元信息、actions、checks"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)

    # ---- 共性 API ----

    def is_dry_run(self, ctx: ActionContext, params: dict[str, Any]) -> bool:
        """统一 dry_run 判定:
        params.dry_run > ctx.vars.dry_run > 环境变量 dry_run_env
        """
        if is_truthy(params.get("dry_run")):
            return True
        if is_truthy(ctx.vars.get("dry_run")):
            return True
        if self.dry_run_env:
            return is_truthy(os.getenv(self.dry_run_env))
        return False

    def setting(
        self,
        params: dict[str, Any],
        key: str,
        *,
        env_var: str | None = None,
        default: Any = None,
    ) -> Any:
        """统一取值链:params[key] > defaults[key] > secrets[key] > os.getenv(env_var) > default

        env_var 仅当显式指定时参与;空字符串视为未设置继续回退;
        值为 "env:VAR" 形式时解析为环境变量值。
        """
        for source in (params, self.defaults, self.secrets):
            value = source.get(key)
            if value is not None:
                if isinstance(value, str) and not value.strip():
                    continue
                return resolve_env_value(value)
        if env_var is not None:
            value = os.getenv(env_var)
            if value:
                return resolve_env_value(value)
        return default

    def error_result(
        self, error: str, *, error_type: str = "unknown_error", **fields: Any
    ) -> dict[str, Any]:
        """统一错误返回构造:{"error":..., "error_type":..., **fields}"""
        return {"error": error, "error_type": error_type, **fields}
```

- [ ] **Step 2: 更新 `plugins/common/helpers.py`**(保留 dry_run_enabled 不动,新增两个函数)

在 `is_truthy` 之后新增:

```python
def resolve_env_value(value: Any) -> Any:
    """若 value 为 "env:VAR" 形式则解析为环境变量值,否则原样返回"""
    if isinstance(value, str) and value.startswith("env:"):
        return os.getenv(value[4:])
    return value


def error_result(
    error: str, *, error_type: str = "unknown_error", **fields: Any
) -> dict[str, Any]:
    """统一错误返回构造(基类 error_result 的纯函数版)"""
    return {"error": error, "error_type": error_type, **fields}
```

- [ ] **Step 3: 更新 `backend/tests/test_plugin_common.py`**

替换 `TestPluginBase` 两个测试(类属性 → __init__ 绑定),并在 `TestDryRunEnabled` 前新增 3 组测试:

```python
class TestPluginBase:
    def test_register_registers_plugin_and_actions_checks(self) -> None:
        def _handler(ctx, params):
            return {}

        def _check(ctx, params):
            return True

        class SamplePlugin(Plugin):
            name = "sample"
            version = "2.0.0"

            def __init__(self, config=None):
                super().__init__(config)
                self.actions = {"sample.run": self._run}
                self.checks = {"sample.ok": self._ok}

            def _run(self, ctx, params):
                return _handler(ctx, params)

            def _ok(self, ctx, params):
                return _check(ctx, params)

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

        p = SamplePlugin()
        assert p.config == {}
        assert p.defaults == {}
        assert p.secrets == {}

        p2 = SamplePlugin(config={"defaults": {"a": 1}, "secrets": {"b": "x"}})
        assert p2.defaults == {"a": 1}
        assert p2.secrets == {"b": "x"}


class TestIsDryRun:
    def test_params_dry_run_wins(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        assert P().is_dry_run(ctx, {"dry_run": True}) is True

    def test_vars_dry_run(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = ActionContext(
            run_id="r", step_id="s", input=None,
            vars={"dry_run": True}, artifacts_dir=tmp_path,
        )
        assert P().is_dry_run(ctx, {}) is True

    def test_env_var(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert P().is_dry_run(ctx, {}) is True

    def test_params_override_env(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.setenv("AUTOFLOW_TEST_DRY_RUN", "1")
        assert P().is_dry_run(ctx, {"dry_run": False}) is False

    def test_default_false(self, tmp_path: Path, monkeypatch) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = _ctx(tmp_path)
        monkeypatch.delenv("AUTOFLOW_TEST_DRY_RUN", raising=False)
        assert P().is_dry_run(ctx, {}) is False

    def test_no_dry_run_env_class_attr(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"

        ctx = _ctx(tmp_path)
        assert P().is_dry_run(ctx, {}) is False

    def test_params_false_overrides_vars_true(self, tmp_path: Path) -> None:
        class P(Plugin):
            name = "p"
            dry_run_env = "AUTOFLOW_TEST_DRY_RUN"

        ctx = ActionContext(
            run_id="r", step_id="s", input=None,
            vars={"dry_run": True}, artifacts_dir=tmp_path,
        )
        assert P().is_dry_run(ctx, {"dry_run": False}) is False


class TestSetting:
    def test_params_priority(self, tmp_path: Path) -> None:
        p = Plugin(config={"defaults": {"k": "d"}, "secrets": {"k": "s"}})
        assert p.setting({"k": "p"}, "k") == "p"

    def test_defaults_then_secrets(self, tmp_path: Path) -> None:
        p = Plugin(config={"defaults": {"k": "d"}, "secrets": {"k": "s"}})
        assert p.setting({}, "k") == "d"
        p2 = Plugin(config={"secrets": {"k": "s"}})
        assert p2.setting({}, "k") == "s"

    def test_env_var_fallback(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({}, "k", env_var="TEST_K") == "env-value"

    def test_env_var_only_when_explicit(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({}, "k") is None

    def test_default_returned_when_missing(self, tmp_path: Path) -> None:
        assert Plugin().setting({}, "k", default="fallback") == "fallback"

    def test_empty_string_falls_through(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        assert Plugin().setting({"k": "  "}, "k", env_var="TEST_K") == "env-value"

    def test_env_prefix_resolution(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("REAL_KEY", "secret-123")
        assert Plugin().setting({"k": "env:REAL_KEY"}, "k") == "secret-123"

    def test_false_is_not_skipped(self, tmp_path: Path) -> None:
        assert Plugin().setting({"k": False}, "k", default="d") is False

    def test_secrets_empty_string_falls_through(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("TEST_K", "env-value")
        p = Plugin(config={"secrets": {"k": "  "}})
        assert p.setting({}, "k", env_var="TEST_K") == "env-value"

    def test_env_missing_prefix_returns_none(self, tmp_path: Path) -> None:
        # params 层显式写 env:MISSING:解析失败返回 None,不再向低层回退
        assert Plugin().setting({"k": "env:MISSING"}, "k", default="d") is None


class TestErrorResult:
    def test_basic(self) -> None:
        r = Plugin().error_result("boom")
        assert r == {"error": "boom", "error_type": "unknown_error"}

    def test_explicit_type_and_fields(self) -> None:
        r = Plugin().error_result(
            "nope", error_type="http_error", status_code=500, body=None
        )
        assert r == {
            "error": "nope",
            "error_type": "http_error",
            "status_code": 500,
            "body": None,
        }


class TestResolveEnvValue:
    def test_env_prefix(self, monkeypatch) -> None:
        monkeypatch.setenv("A", "1")
        assert resolve_env_value("env:A") == "1"

    def test_env_prefix_unset_returns_none(self) -> None:
        assert resolve_env_value("env:NOT_SET_ANYWHERE") is None

    def test_plain_value_passthrough(self) -> None:
        assert resolve_env_value("plain") == "plain"
        assert resolve_env_value(42) == 42
```

同时更新 import 行(**保留 `dry_run_enabled`**,新增 `resolve_env_value`;dry_run_enabled 与其导入在 Task 8 一并删除):

```python
from plugins.common.helpers import (
    dry_run_enabled,
    is_truthy,
    read_text,
    resolve_env_value,
    safe_name,
    utc_now_iso,
    write_text,
)
```

`TestDryRunEnabled` 类(原 helpers.dry_run_enabled 的 4 个测试)保留到 Task 8 删除(依赖上面的 import)。

- [ ] **Step 4: 运行单测验证**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && PYTHONPATH=backend:. pytest backend/tests/test_plugin_common.py -q`
Expected: PASS(原 16 + 新增 22 个用例 = 38;TestPluginBase 2 个为 1:1 改造,净增 0)

- [ ] **Step 5: 全量回归(确认兼容过渡有效)**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 117 passed(95 基线 + 22 新增;旧插件仍用类属性 actions,被基类复制进实例)

> **ruff 提示**:本任务与后续所有任务的代码块均需通过 ruff(E501 行宽 88/format)。复制代码后先运行 `ruff format backend plugins && ruff check backend plugins`,修正任何行宽问题后再提交,否则 pre-commit 的 ruff hook 会拦截 commit。

- [ ] **Step 6: Commit**

```bash
git add plugins/common/plugin.py plugins/common/helpers.py backend/tests/test_plugin_common.py
git commit -m "refactor(plugins): enhance Plugin base with is_dry_run/setting/error_result"
```

---

## Task 2: 迁移 dummy 插件为类方法形态

**Files:**
- Modify: `plugins/dummy/backend.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/dummy/backend.py`**

```python
# @file /plugins/dummy/backend.py
# @brief Dummy 插件：回传用户输入信息（测试用）
# @create 2026-02-21 00:00:00
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext

from plugins.common.plugin import Plugin


class DummyPlugin(Plugin):
    """Dummy 插件：回传用户输入信息（测试用）"""

    name = "dummy"
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "dummy.echo": self._echo,
        }
        self.checks = {}

    def _echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


PLUGIN = DummyPlugin
```

- [ ] **Step 2: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 117 passed(dummy 无独立测试文件,由 loader/端到端覆盖)

- [ ] **Step 3: Commit**

```bash
git add plugins/dummy/backend.py
git commit -m "refactor(plugins): migrate dummy plugin to class methods"
```

---

## Task 3: 迁移 desktop_checkin 插件为类方法形态(最大迁移)

**Files:**
- Modify: `plugins/desktop_checkin/backend.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/desktop_checkin/backend.py`**

```python
# @file /plugins/desktop_checkin/backend.py
# @brief 桌面自动打卡插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)
# @update 2026-08-11 迁移为类方法形态,dry_run 统一走 self.is_dry_run

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext

from plugins.common.helpers import is_truthy, safe_name
from plugins.common.plugin import Plugin


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / path).resolve()


class DesktopCheckinPlugin(Plugin):
    """桌面自动打卡插件"""

    name = "desktop-checkin"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_DESKTOP_DRY_RUN"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
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
        title = str(params.get("title", ""))
        if not title:
            raise ValueError("title is required")

        timeout_seconds = float(params.get("timeout_seconds", 0))
        use_regex = is_truthy(params.get("regex"))
        focus = is_truthy(params.get("focus", True))

        if self.is_dry_run(ctx, params):
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

    def _click(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        x = int(params["x"])
        y = int(params["y"])
        button = str(params.get("button", "left"))
        clicks = int(params.get("clicks", 1))
        interval = float(params.get("interval", 0))

        if self.is_dry_run(ctx, params):
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

    def _double_click(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        params = dict(params)
        params["clicks"] = 2
        return self._click(ctx, params)

    def _drag(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        from_x = int(params["from_x"])
        from_y = int(params["from_y"])
        to_x = int(params["to_x"])
        to_y = int(params["to_y"])
        duration = float(params.get("duration", 0))
        button = str(params.get("button", "left"))

        if self.is_dry_run(ctx, params):
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

    def _type_text(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        text = str(params.get("text", ""))
        interval = float(params.get("interval", 0))
        secret = is_truthy(params.get("secret"))

        if self.is_dry_run(ctx, params):
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

    def _hotkey(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        keys = params.get("keys")
        if not isinstance(keys, list) or not keys:
            raise ValueError("keys must be a non-empty list")
        keys = [str(k) for k in keys]

        if self.is_dry_run(ctx, params):
            return {"sent": True, "keys": keys, "dry_run": True}

        import pyautogui

        pyautogui.hotkey(*keys)
        return {"sent": True, "keys": keys, "dry_run": False}

    def _wait(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        seconds = float(params.get("seconds", 0))
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        dry_run = self.is_dry_run(ctx, params)
        if not dry_run:
            time.sleep(seconds)
        return {"waited_seconds": seconds, "dry_run": dry_run}

    def _screenshot(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
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

        if self.is_dry_run(ctx, params):
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

    def _image_exists(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
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

    def _window_title_contains(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
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


PLUGIN = DesktopCheckinPlugin
```

- [ ] **Step 2: 运行桌面插件端到端测试**

Run: `PYTHONPATH=backend:. pytest plugins/desktop_checkin/tests -q`
Expected: 2 passed(dry_run 流程 + actions 列表)

- [ ] **Step 3: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 117 passed

- [ ] **Step 4: Commit**

```bash
git add plugins/desktop_checkin/backend.py
git commit -m "refactor(plugins): migrate desktop_checkin plugin to class methods"
```

---

## Task 4: 迁移 zhihu_digest 插件为类方法形态(cookie 收敛为 setting)

**Files:**
- Modify: `plugins/zhihu_digest/backend.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/zhihu_digest/backend.py`**

行为契约:返回值结构不变;`_get_cookie` 保持原优先级 `params.cookie → params.cookie_env → ZHIHU_COOKIE`(顺序经审核修正,不得再翻转);新增能力:config.yaml `defaults.cookie`/`secrets.cookie`(若配置)作为环境变量之前的回退层。

```python
# @file /plugins/zhihu_digest/backend.py
# @brief 知乎回答总结插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)
# @update 2026-08-11 迁移为类方法形态,cookie 解析收敛为 self.setting

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.core.registry import ActionContext

from plugins.common.helpers import read_text, resolve_env_value, utc_now_iso, write_text
from plugins.common.plugin import Plugin


def _parse_answer_url(url: str) -> tuple[str | None, str | None]:
    m = re.search(r"/question/(\d+)/answer/(\d+)", url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


class ZhihuDigestPlugin(Plugin):
    """知乎回答总结插件"""

    name = "zhihu-digest"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_ZHIHU_DRY_RUN"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "zhihu.fetch_answer": self._fetch_answer,
            "zhihu.post_answer_draft": self._post_answer_draft,
        }
        self.checks = {}

    def _get_cookie(self, params: dict[str, Any]) -> str | None:
        """cookie 取值(保持原优先级):
        1. params.cookie(env: 前缀由 resolve_env_value 解析)
        2. params.cookie_env 指定的环境变量
        3. setting() 链:defaults.cookie > secrets.cookie > ZHIHU_COOKIE(新增能力)"""
        cookie = params.get("cookie")
        if isinstance(cookie, str) and cookie.strip():
            return resolve_env_value(cookie)

        env_name = params.get("cookie_env")
        if isinstance(env_name, str) and env_name.strip():
            return os.getenv(env_name) or None

        return self.setting({}, "cookie", env_var="ZHIHU_COOKIE")

    def _fetch_answer(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        url = str(params.get("url", "")).strip()
        if not url:
            raise ValueError("url is required")

        question_id, answer_id = _parse_answer_url(url)
        if question_id is None or answer_id is None:
            raise ValueError("unsupported zhihu answer url")

        if self.is_dry_run(ctx, params):
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
        cookie = self._get_cookie(params)

        if mode in {"auto", "playwright"}:
            return self._fetch_answer_playwright(
                ctx=ctx,
                url=url,
                question_id=question_id,
                answer_id=answer_id,
                timeout_seconds=timeout_seconds,
                cookie=cookie,
            )
        raise ValueError(f"unsupported mode: {mode}")

    def _fetch_answer_playwright(
        self,
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
                title = page.locator("h1.QuestionHeader-title").first.inner_text().strip()
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

    def _post_answer_draft(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
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

        if self.is_dry_run(ctx, params):
            return {"attempted": False, "saved_path": rel, "dry_run": True}

        cookie = self._get_cookie(params)
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


PLUGIN = ZhihuDigestPlugin
```

- [ ] **Step 2: 运行知乎插件端到端测试**

Run: `PYTHONPATH=backend:. pytest plugins/zhihu_digest/tests -q`
Expected: 2 passed(dry_run 流程 + actions 列表)

- [ ] **Step 3: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 117 passed

- [ ] **Step 4: Commit**

```bash
git add plugins/zhihu_digest/backend.py
git commit -m "refactor(plugins): migrate zhihu_digest plugin to class methods"
```

---

## Task 5: 迁移 ai_deepseek 插件为类方法形态(api_key 收敛为 setting)

**Files:**
- Modify: `plugins/ai_deepseek/backend.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/ai_deepseek/backend.py`**

行为契约:返回值结构不变。`DeepSeekClient` 保持独立类。`_get_deepseek_api_key` 收敛为 `self.setting(params, "api_key", env_var="DEEPSEEK_API_KEY")`;原实现中 `env:XXX` 环境变量未设置时返回字面 "env:XXX" 作为 key 的行为,修正为回退/raise(更早失败,属明确改进)。

```python
# @file /plugins/ai_deepseek/backend.py
# @brief DeepSeek AI 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI(工具函数收敛至 plugins.common.helpers)
# @update 2026-08-11 迁移为类方法形态,api_key 解析收敛为 self.setting

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from app.core.registry import ActionContext

from plugins.common.helpers import read_text, write_text
from plugins.common.plugin import Plugin


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


class AIDeepSeekPlugin(Plugin):
    """DeepSeek AI 插件"""

    name = "ai-deepseek"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_AI_DRY_RUN"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "ai.deepseek_summarize": self._deepseek_summarize,
        }
        self.checks = {}

    def _get_deepseek_api_key(self, params: dict[str, Any]) -> str:
        """api_key 取值链:params.api_key > defaults.api_key > secrets.api_key > DEEPSEEK_API_KEY"""
        key = self.setting(params, "api_key", env_var="DEEPSEEK_API_KEY")
        if key:
            return key
        raise RuntimeError("missing DEEPSEEK_API_KEY")

    def _deepseek_summarize(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
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

        if self.is_dry_run(ctx, params):
            summary = "（dry_run）示例总结：要点已整理。"
            out_rel = write_text(ctx, "ai/summary.md", summary)
            return {
                "summary_path": out_rel,
                "prompt_path": prompt_rel,
                "dry_run": True,
                "provider": "deepseek",
            }

        api_key = self._get_deepseek_api_key(params)
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


PLUGIN = AIDeepSeekPlugin
```

- [ ] **Step 2: 新增 `plugins/ai_deepseek/tests/test_ai_deepseek_plugin.py`(api_key 取值链单测)**

```python
# @file /plugins/ai_deepseek/tests/test_ai_deepseek_plugin.py
# @brief ai_deepseek api_key 取值链单测
# @create 2026-08-11

from __future__ import annotations

import pytest

from plugins.ai_deepseek.backend import AIDeepSeekPlugin


def _plugin(config=None) -> AIDeepSeekPlugin:
    return AIDeepSeekPlugin(config)


def test_api_key_from_params() -> None:
    assert _plugin()._get_deepseek_api_key({"api_key": "k-123"}) == "k-123"


def test_api_key_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("MY_KEY", "k-env")
    assert _plugin()._get_deepseek_api_key({"api_key": "env:MY_KEY"}) == "k-env"


def test_api_key_from_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k-secret")
    assert _plugin(config={"secrets": {"api_key": "k-secret"}})._get_deepseek_api_key({}) == "k-secret"


def test_api_key_missing_raises(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="missing DEEPSEEK_API_KEY"):
        _plugin()._get_deepseek_api_key({})
```

Run: `PYTHONPATH=backend:. pytest plugins/ai_deepseek/tests -q`
Expected: 4 passed

- [ ] **Step 3: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 121 passed(117 + 4)

- [ ] **Step 4: Commit**

```bash
git add plugins/ai_deepseek/backend.py plugins/ai_deepseek/tests/test_ai_deepseek_plugin.py
git commit -m "refactor(plugins): migrate ai_deepseek plugin to class methods"
```

---

## Task 6: 迁移 openclaw 插件为类方法形态(删除模块级状态)

**Files:**
- Modify: `plugins/openclaw/backend.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/openclaw/backend.py`**

删除模块级 `_DEFAULTS`/`_SECRETS` 及 `__init__` 中的 clear/update 注入,改由基类实例属性 `self.defaults`/`self.secrets` 提供;三个 action 的错误返回收敛为 `self.error_result()`。注意 `url is required` 分支原返回**不含** error_type 键,保持字面 dict 不变(契约优先)。

```python
# @file /plugins/openclaw/backend.py
# @brief OpenClaw 插件后端实现
# @create 2026-03-15 00:00:00
# @update 2026-08-10 迁移为 Plugin 基类新 ABI
# @update 2026-08-11 迁移为类方法形态,config 经基类实例属性 self.defaults/self.secrets 访问

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


class OpenClawPlugin(Plugin):
    """OpenClaw 插件:HTTP 请求、命令执行、KnowFlow 记录"""

    name = "openclaw"
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "openclaw.http_request": self._http_request,
            "openclaw.exec": self._exec_command,
            "openclaw.knowflow_record": self._knowflow_record,
        }
        self.checks = {
            "openclaw.status_code_ok": self._status_code_ok,
            "openclaw.exit_code_zero": self._exit_code_zero,
        }

    def _http_request(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        method = params.get("method", "GET").upper()
        url = params.get("url")
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout") or self.defaults.get("http_timeout", 30)

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
            return self.error_result(
                str(e),
                error_type="http_error",
                status_code=e.code,
                headers=dict(e.headers) if e.headers else {},
                body=e.read().decode("utf-8") if e.fp else None,
            )
        except URLError as e:
            return self.error_result(
                str(e.reason),
                error_type="network_error",
                status_code=None,
                headers=None,
                body=None,
            )
        except Exception as e:
            return self.error_result(
                str(e),
                error_type="unknown_error",
                status_code=None,
                headers=None,
                body=None,
            )

    def _exec_command(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a shell command with optional safety controls.

        Security note: When safe_mode is False, commands run with shell=True,
        which is vulnerable to command injection. Only disable safe_mode when
        you fully trust the command source.
        """
        command = params.get("command")
        args = params.get("args")  # 可选参数列表
        cwd = params.get("cwd")

        # Convert timeout to float; guard against YAML string values
        timeout_raw = params.get("timeout") or self.defaults.get("exec_timeout", 60)
        try:
            timeout = float(timeout_raw)
        except (TypeError, ValueError):
            timeout = 60.0

        safe_mode = params.get("safe_mode", self.defaults.get("safe_mode", True))
        allowed_commands = self.defaults.get("allowed_commands", [])

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
            return self.error_result(
                "timeout",
                error_type="timeout",
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
            )
        except Exception as e:
            return self.error_result(
                str(e),
                error_type="unknown_error",
                exit_code=-1,
                stdout="",
                stderr=str(e),
            )

    def _knowflow_record(self, ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
        default_base_url = (
            self.secrets.get("knowflow_base_url")
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
            return self.error_result(
                f"HTTP {e.code}: {error_body}",
                error_type="http_error",
                item_id=None,
                name=name,
                success=False,
            )
        except URLError as e:
            return self.error_result(
                str(e.reason),
                error_type="network_error",
                item_id=None,
                name=name,
                success=False,
            )
        except Exception as e:
            return self.error_result(
                str(e),
                error_type="unknown_error",
                item_id=None,
                name=name,
                success=False,
            )

    def _status_code_ok(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        expected = params.get("expected", 200)
        action_output = ctx.action_output

        if not action_output:
            return False

        status_code = action_output.get("status_code")
        return status_code == expected

    def _exit_code_zero(self, ctx: CheckContext, params: dict[str, Any]) -> bool:
        action_output = ctx.action_output

        if not action_output:
            return False

        exit_code = action_output.get("exit_code")
        return exit_code == 0


PLUGIN = OpenClawPlugin
```

- [ ] **Step 2: 新增 `plugins/openclaw/tests/test_openclaw_plugin.py`(错误返回/白名单单测)**

```python
# @file /plugins/openclaw/tests/test_openclaw_plugin.py
# @brief openclaw 错误返回与安全控制单测
# @create 2026-08-11

from __future__ import annotations

from unittest.mock import patch

from plugins.openclaw.backend import OpenClawPlugin


def _plugin(config=None) -> OpenClawPlugin:
    return OpenClawPlugin(config)


class _Ctx:
    run_id = "r"
    step_id = "s"
    input = None
    vars = {}
    artifacts_dir = "/tmp"


def test_http_request_missing_url_keeps_literal_dict() -> None:
    # 契约:url is required 分支不含 error_type 键
    result = _plugin()._http_request(_Ctx(), {})
    assert result == {
        "error": "url is required",
        "status_code": None,
        "headers": None,
        "body": None,
    }


def test_exec_command_missing_command() -> None:
    result = _plugin()._exec_command(_Ctx(), {})
    assert result["error"] == "command is required"
    assert result["exit_code"] is None


def test_exec_command_denied_by_whitelist() -> None:
    plugin = _plugin(config={"defaults": {"allowed_commands": [r"^ls$"]}})
    result = plugin._exec_command(_Ctx(), {"command": "rm -rf /"})
    assert result["error"] == "command_not_allowed"
    assert result["exit_code"] == -1


def test_exec_command_timeout_uses_error_result() -> None:
    import subprocess

    def _raise(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    with patch("plugins.openclaw.backend.subprocess.run", side_effect=_raise):
        result = _plugin()._exec_command(_Ctx(), {"command": "sleep 100"})
    assert result["error"] == "timeout"
    assert result["error_type"] == "timeout"
    assert result["exit_code"] == -1
```

Run: `PYTHONPATH=backend:. pytest plugins/openclaw/tests -q`
Expected: 4 passed

- [ ] **Step 3: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 125 passed(121 + 4)

- [ ] **Step 4: grep 确认模块级状态已删除**

Run: `rg -n "_DEFAULTS|_SECRETS" plugins/openclaw/`
Expected: 无输出(0 命中)

- [ ] **Step 5: Commit**

```bash
git add plugins/openclaw/backend.py plugins/openclaw/tests/test_openclaw_plugin.py
git commit -m "refactor(plugins): migrate openclaw plugin to class methods"
```

---

## Task 7: 迁移 examples 插件为类方法形态

**Files:**
- Modify: `plugins/examples/hello_world.py`(全文替换)
- Modify: `plugins/examples/dummy_echo.py`(全文替换)

- [ ] **Step 1: 重写 `plugins/examples/hello_world.py`**

```python
# @file /plugins/examples/hello_world.py
# @brief 示例插件：注册 core.hello action
# @create 2026-08-09
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class HelloWorldPlugin(Plugin):
    """示例插件：注册 core.hello action"""

    name = "hello-world"
    version = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "core.hello": self._hello,
        }
        self.checks = {}

    def _hello(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        name = params.get("name", "World")
        return {"message": f"Hello, {name} from AutoFlow!"}


PLUGIN = HelloWorldPlugin
```

- [ ] **Step 2: 重写 `plugins/examples/dummy_echo.py`**

```python
# @file /plugins/examples/dummy_echo.py
# @brief 示例插件：注册 dummy.echo action,回传用户输入信息
# @create 2026-02-21 00:00:00
# @update 2026-08-11 迁移为类方法形态

from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class DummyEchoPlugin(Plugin):
    """示例插件：注册 dummy.echo action"""

    name = "dummy-echo"
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "dummy.echo": self._echo,
        }
        self.checks = {}

    def _echo(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        return {
            "input": ctx.input,
            "message": params.get("message"),
            "vars": ctx.vars,
        }


PLUGIN = DummyEchoPlugin
```

- [ ] **Step 3: 文件插件加载回归(test_plugin_loader 的 file plugin 用例)**

Run: `PYTHONPATH=backend:. pytest backend/tests/test_plugin_loader.py -q`
Expected: PASS(文件插件模块名解析用例覆盖 examples 形态)

- [ ] **Step 4: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 125 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/examples/hello_world.py plugins/examples/dummy_echo.py
git commit -m "refactor(plugins): migrate example plugins to class methods"
```

---

## Task 8: 清理过渡代码(dry_run_enabled 删除、基类兼容合并移除)

**Files:**
- Modify: `plugins/common/helpers.py`(删除 dry_run_enabled)
- Modify: `plugins/common/plugin.py`(移除类属性兼容合并与类属性默认)
- Modify: `plugins/common/__init__.py`(**必改**:移除 dry_run_enabled 的 import 与 `__all__` 条目,否则包导入即 ImportError,所有插件加载失败)
- Modify: `backend/tests/test_plugin_common.py`(删除 TestDryRunEnabled)

- [ ] **Step 1: `plugins/common/helpers.py` 删除 `dry_run_enabled` 函数**(整段移除;import os 保留,resolve_env_value 依赖)

- [ ] **Step 2: `plugins/common/plugin.py` 移除兼容合并与类属性默认**

将:

```python
    actions: dict[str, ActionHandler] = {}  # 类属性默认(兼容旧 ABI);Task 8 移除
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))
        self.secrets = dict(self.config.get("secrets", {}))
        # 兼容过渡:复制子类类属性声明(旧 ABI);新 ABI 在子类 __init__ 覆盖为实例绑定方法
        self.actions: dict[str, ActionHandler] = dict(type(self).actions)
        self.checks: dict[str, CheckHandler] = dict(type(self).checks)
```

替换为:

```python
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.defaults = dict(self.config.get("defaults", {}))
        self.secrets = dict(self.config.get("secrets", {}))
        self.actions: dict[str, ActionHandler] = {}
        self.checks: dict[str, CheckHandler] = {}
```

同时将文件头注释中"(Task 8 移除类属性兼容合并)"更新为"actions/checks 实例属性化"。

- [ ] **Step 3: `plugins/common/__init__.py` 移除 dry_run_enabled**

将 import 块与 `__all__` 中的 `dry_run_enabled` 条目删除(其余导出不变)。

- [ ] **Step 4: `backend/tests/test_plugin_common.py` 删除 `TestDryRunEnabled` 类**(4 个用例;其行为已由 Task 1 新增的 `TestIsDryRun` 覆盖),并移除 import 行的 `dry_run_enabled`

- [ ] **Step 5: grep 确认无残留**

Run: `rg -n "dry_run_enabled" plugins/ backend/ --glob '!**/__pycache__/**'`
Expected: 无输出(0 命中)

- [ ] **Step 6: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 121 passed(125 - 4 旧 dry_run_enabled 用例)

- [ ] **Step 7: Commit**

```bash
git add plugins/common/helpers.py plugins/common/plugin.py plugins/common/__init__.py backend/tests/test_plugin_common.py
git commit -m "refactor(plugins): remove dry_run_enabled and class-attr compat shim"
```

---

## Task 9: 文档同步(zh/en 插件开发指南 + plugin-sdk)

**Files:**
- Modify: `docs/zh/plugin-dev-guide.md`
- Modify: `docs/en/plugin-dev-guide.md`
- Modify: `docs/zh/specs/plugin-sdk.md`

- [ ] **Step 1: 更新 `docs/zh/plugin-dev-guide.md` 中 ABI 示例**

将"新建插件"示例替换为类方法形态(以 hello_world 为模板):

```python
from __future__ import annotations

from typing import Any

from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


class MyPlugin(Plugin):
    """我的插件"""

    name = "my-plugin"
    version = "0.1.0"
    dry_run_env = "AUTOFLOW_MY_DRY_RUN"  # 可选:部署级 dry_run 开关

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.actions = {
            "my.action": self._action,
        }
        self.checks = {}

    def _action(self, ctx: ActionContext, params: dict[str, Any]) -> Any:
        if self.is_dry_run(ctx, params):
            return {"dry_run": True, ...}
        # 配置取值:params > defaults > secrets > env > default
        key = self.setting(params, "key", env_var="MY_KEY", default="d")
        ...
        return {"dry_run": False, ...}


PLUGIN = MyPlugin
```

同步更新文档中说明段落:handlers 为实例方法;`is_dry_run`/`setting`/`error_result` 为基类共性 API;config.yaml 的 `defaults`/`secrets` 由基类归一为实例属性。

- [ ] **Step 2: 更新 `docs/en/plugin-dev-guide.md`**(与 Step 1 同内容英文版)

- [ ] **Step 3: 更新 `docs/zh/specs/plugin-sdk.md`**

将协议描述中的旧 ABI(模块级函数 + 类属性 actions)更新为:类方法形态、`PLUGIN` 导出不变、基类共性 API 列表。保留 loader 加载流程描述(不变)。

- [ ] **Step 4: grep 确认文档无旧 ABI 残留**

Run: `rg -n "def _echo\(ctx|dry_run_enabled|^actions = \{" docs/zh/plugin-dev-guide.md docs/en/plugin-dev-guide.md docs/zh/specs/plugin-sdk.md`
Expected: 无输出(0 命中;`^actions = {` 锚定行首,避免误匹配新版 `self.actions = {` 示例;允许文档中刻意展示旧->新对照的部分除外)

- [ ] **Step 5: Commit**

```bash
git add docs/zh/plugin-dev-guide.md docs/en/plugin-dev-guide.md docs/zh/specs/plugin-sdk.md
git commit -m "docs: update plugin guides and sdk spec for class-method ABI"
```

---

## Task 10: runner.py 去重(模板 context + StepResult 工厂)

**Files:**
- Modify: `backend/app/runtime/runner/runner.py`

- [ ] **Step 1: 提取 `_template_context` 私有方法**

在 `_run_hooks` 之前新增:

```python
    def _template_context(
        self,
        step_outputs: dict[str, Any],
        runtime_vars: dict[str, Any],
        current_input: Any,
    ) -> dict[str, Any]:
        """统一模板解析上下文构造(消除 4 处重复)"""
        return {
            "steps": step_outputs,
            "vars": runtime_vars,
            "input": current_input,
        }
```

- [ ] **Step 2: 将 4 处 `resolve_templates` 调用改为使用 `self._template_context`**

4 处位置(原代码字面 `{"steps": step_outputs, "vars": runtime_vars, "input": current_input}` 的构造):

1. `_run_hooks` 内(约 61 行)
2. `_execute_once` 内 action params(约 107 行)
3. `_execute_step` 内 for_each(约 172 行)
4. `run_flow` 内 condition(约 257 行)

每处替换为:

```python
                resolved_params = resolve_templates(
                    step.action.params,
                    self._template_context(step_outputs, runtime_vars, current_input),
                )
```

(condition/for_each/hooks 处同理,保持各自原调用形态,仅替换 context 字面量为 `self._template_context(...)` 调用。)

- [ ] **Step 3: 提取 `_make_step_result` 私有工厂**

在 `run_flow` 之前新增:

```python
    def _make_step_result(
        self,
        *,
        step_id: str,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        action_output: Any,
        check_passed: bool | None,
        error: str | None,
        iterations: list[dict] | None = None,
    ) -> StepResult:
        """统一 StepResult 构造(消除 skipped/正常两处重复)"""
        return StepResult(
            step_id=step_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            action_output=action_output,
            check_passed=check_passed,
            error=error,
            iterations=iterations,
        )
```

- [ ] **Step 4: 替换 run_flow 中两处 StepResult 构造**

skipped 分支(约 267 行)替换为:

```python
                    run.steps.append(
                        self._make_step_result(
                            step_id=step.id,
                            status="skipped",
                            started_at=step_started,
                            finished_at=step_finished,
                            action_output=None,
                            check_passed=None,
                            error=None,
                        )
                    )
```

正常分支(约 302 行)替换为:

```python
            run.steps.append(
                self._make_step_result(
                    step_id=step.id,
                    status="success" if success else "failed",
                    started_at=step_started,
                    finished_at=step_finished,
                    action_output=action_output,
                    check_passed=check_passed,
                    error=step_error,
                    iterations=iterations,
                )
            )
```

- [ ] **Step 5: 全量回归(行为零变化)**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 121 passed(runner 被 control_flow/foreach/hooks 等测试覆盖)

- [ ] **Step 6: Commit**

```bash
git add backend/app/runtime/runner/runner.py
git commit -m "refactor(backend): dedup template context and StepResult construction in runner"
```

---

## Task 11: registry 注释 / setting_manager 收敛 / loader 注释

**Files:**
- Modify: `backend/app/core/registry.py`(注释)
- Modify: `backend/app/core/setting_manager.py`(默认值收敛)
- Modify: `backend/app/runtime/plugin_loader.py`(注释)

- [ ] **Step 1: `backend/app/core/registry.py` 更新头注释与类 docstring**

将:

```python
# @brief 全局注册表 - Action/Check 注册表与插件清单（基于 Hook 模式）
```

替换为:

```python
# @brief 全局注册表 - Action/Check 注册表与插件清单(基于 Plugin 注册模式)
```

类 docstring"通过 hook 系统注册 actions 和 checks"替换为"通过 Plugin 基类的 register() 注册 actions 和 checks"。

- [ ] **Step 2: `backend/app/core/setting_manager.py` 收敛默认值双处定义**

注意:`--port` **不收敛**(保留 `default=int(os.getenv("PORT", "3001"))` 原样)——`_load_env` 中 `config["PORT"]` 默认是 `BACKEND_INTERNAL_PORT`(3000),若改为读 `self.config` 会把默认端口从 3001 变成 3000,造成行为回归(审核发现)。`--host`/`--log-level`/`--cors-origins` 三个的 default 改为读取 `self.config`(已由 `_load_env` 填充,`setdefault` 语义与现状一致):

```python
        group.add_argument(
            "--host",
            type=str,
            default=self.config.get("HOST", "0.0.0.0"),
            help="绑定地址 (默认: 0.0.0.0)",
        )

        group.add_argument(
            "--port",
            type=int,
            default=os.getenv("PORT", "3001"),
            help="绑定端口 (默认: 3001)",
        )

        group.add_argument(
            "--log-level",
            type=str,
            default=self.config.get("LOG_LEVEL", "INFO"),
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"],
            help="日志级别 (默认: INFO)",
        )

        group.add_argument(
            "--cors-origins",
            type=str,
            default=self.config.get("CORS_ORIGINS", "*"),
            help="CORS 允许的源，逗号分隔 (默认: *)",
        )
```

`init()` 中三处 `getattr(args, x, self.config.get(...))` 收敛为私有局部 helper(注意 config 键大写,回退键用 `name.upper()`):

```python
        def _arg(name: str, default: Any) -> Any:
            return getattr(args, name, self.config.get(name.upper(), default))

        self.config["HOST"] = _arg("host", "0.0.0.0")
        self.config["PORT"] = _arg("port", 3001)
        self.config["LOG_LEVEL"] = _arg("log_level", "INFO")

        cors_origins_val = _arg("cors_origins", "*")
```

注意:CORS_ORIGINS 处理逻辑(列表/逗号拆分)保持不变。行为零变化:--host/--log-level/--cors-origins 的 argparse 默认与 `_load_env` setdefault 同源;--port 保持原默认(3001)。

- [ ] **Step 3: `backend/app/runtime/plugin_loader.py` 同步 docstring**

`load_plugins` docstring 中"插件模块需暴露 PLUGIN = XxxPlugin (Plugin 子类),见 plugins/common/plugin.py"追加"handlers 为实例方法,由插件 __init__ 绑定到 self.actions/self.checks"。文件头 `@update` 追加 `2026-08-11 注释同步类方法 ABI`。

- [ ] **Step 4: 全量回归**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 121 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/registry.py backend/app/core/setting_manager.py backend/app/runtime/plugin_loader.py
git commit -m "refactor(backend): update stale comments and dedup setting defaults"
```

---

## Task 12: 全量验证

**Files:** 无(纯验证)

- [ ] **Step 1: 完整测试**

Run: `PYTHONPATH=backend:. pytest backend/tests plugins -q`
Expected: 121 passed

- [ ] **Step 2: ruff 检查与格式**

Run: `ruff check backend plugins && ruff format --check backend plugins`
Expected: 无错误、无格式差异(如 pre-commit ruff hook 在 commit 时失败,先手动 `ruff check --fix` + `ruff format` 再 `git add` 重新 commit)

- [ ] **Step 3: 残留 grep 全量确认**

Run: `rg -n "_DRY_RUN_ENV|_DEFAULTS|_SECRETS|dry_run_enabled" plugins/ backend/ --glob '!**/__pycache__/**'`
Expected: 无输出(0 命中)

- [ ] **Step 4: 后端启动冒烟(插件加载 + execute)**

基线(实施前实测):actions=17(builtin 2: core.log/core.sleep + 插件 15)、plugins=6(含 builtin)、checks=6、errors 字段名为 `errors`。重构后计数必须一致。

启动(注意:venv 位于 `backend/.venv`,非仓库根;AGENTS.md 要求走 `scripts/start.sh`,此处为单进程冒烟显式豁免,若环境允许优先用 `scripts/start.sh local backend`):

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow && env PYTHONPATH=backend:. backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 3001 &
SMOKE_PID=$!
sleep 3
```

随后:

```bash
curl -s http://127.0.0.1:3001/api/v1/plugins | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['actions']), 'actions,', len(d['plugins']), 'plugins,', len(d['errors']), 'errors')"
curl -s -X POST http://127.0.0.1:3001/api/v1/runs/execute -H 'Content-Type: application/json' -d '{"flow_yaml": "version: \"1\"\nname: \"smoke\"\nsteps:\n  - id: \"echo\"\n    action:\n      type: \"dummy.echo\"\n      params:\n        message: \"ok\"\n"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'], d['steps'][0]['status'])"
```

Expected: `17 actions, 6 plugins, 0 errors`(与基线一致);execute 返回 `success success`。清理:

```bash
kill $SMOKE_PID 2>/dev/null; pkill -f "uvicorn app.main:app" 2>/dev/null
```

- [ ] **Step 5: git 状态确认**

Run: `git status --short && git log --oneline -15`
Expected: 工作区干净;最近 15 条提交中包含本计划全部 12 条任务 commit(不含 spec/plan 文档提交 c7243ff 之前的旧提交可能挤出列表,以 `git log --oneline c7243ff..HEAD` 核对 12 条为准)

- [ ] **Step 6: 汇总报告**

向用户报告:完成的任务清单、121 passed 测试结果、冒烟结果(17/6/0 + execute)、全部 commit 列表(含 hash)。
