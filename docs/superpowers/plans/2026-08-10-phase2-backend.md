# 阶段二:后端 — 序列化统一 / 模型映射 / loader 收敛 / 死代码清理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变后端行为的前提下完成四件事:将 store/runner 三处重叠的深拷贝/序列化逻辑收敛为 `app/runtime/utils/serialization.py` 的 `safe_deep_copy`/`to_jsonable`;为 `PluginItem`/`PluginErrorItem` 增加 `from_info` 工厂并收拢 `api/v1/plugins.py` 映射样板;将 `plugin_loader.py` 收敛为 PLUGIN 协议最终形态并补齐文件插件用例;删除 `setting_manager` 的 DB/Redis 死配置与 `env_secrets` 死代码。全部 pytest(95 passed)与 ruff 通过,`/health`、`/plugins`、`/runs/execute` 冒烟正常。

**Architecture:** 序列化统一为核心:新增 `serialization.py`,`safe_deep_copy` 以引用跟踪打断循环引用(兼容原 `_deep_copy_with_ref_tracking` 与 `_deep_copy_or_str` 两种行为,是后者的超集),`to_jsonable` 以 JSON 往返打断循环引用(等价原 `_to_vars_value`);store 与 runner 改为引用统一实现后删除私有函数。模型映射在 pydantic 模型上增加类工厂方法,API 层推导式收拢为工厂调用。loader 已在阶段一完成 PLUGIN 识别/注入/注册与 register 协议删除,本阶段只做注释清理与文件插件形态的测试补强。死代码清理先 grep 确认无引用再删除,避免误删。

**Tech Stack:** Python 3.12、pytest 9、ruff 0.16(格式 `ruff format`,lint `ruff check`)、FastAPI/TestClient、pydantic v2。命令统一从 `backend/` 目录执行 pytest 与 ruff;`plugins` 包位于仓库根目录,测试通过 `backend/tests/conftest.py`(阶段一已建)把仓库根加入 `sys.path`。

---

## 0. 前置状态(阶段一最终形态)与约定

本计划假设阶段一计划(`docs/superpowers/plans/2026-08-10-phase1-plugin-abi.md`)已完整执行,仓库处于其最终形态:

1. `plugins/common/{__init__.py, plugin.py, helpers.py}` 已存在:`Plugin` 基类(声明式 `name/version/actions/checks` + `register(registry)`)、6 个共享 helpers。目录插件不注册进 `plugins.yaml`。
2. 5 个目录插件与 2 个文件示例插件均已迁移为 `class XxxPlugin(Plugin)` 并导出 `PLUGIN`;`plugins/*/hooks.py` 全部删除;`__init__.py` 仅导出 `PLUGIN`。
3. `plugin_loader.py` 已识别 `PLUGIN`(Plugin 子类)实例化并注入 config,调用 `plugin.register(registry)`;`getattr(module, "register")` 协议已删除;目录/文件两种模块名解析保留;加载失败经 `registry.add_plugin_error` 上报,不影响其他插件。
4. `backend/tests/conftest.py` 已把仓库根目录加入 `sys.path`;`backend/tests/test_plugin_loader.py`(10 个用例)、`backend/tests/test_plugin_common.py`(16 个用例)已存在。
5. 全量测试基线:`cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q` → `83 passed`。

**阶段二约定**:

- 全量测试命令统一为:
  `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
- ruff 校验命令统一为:
  `cd backend && .venv/bin/ruff check app tests ../plugins && .venv/bin/ruff format --check app tests ../plugins`
  预期输出:`All checks passed!` 与 `N files already formatted`(exit code 0)。
- commit 风格遵循仓库惯例:本阶段统一使用 `refactor(backend):` 前缀,每个任务独立 commit。
- 文件头注释惯例:`# @file` / `# @brief` / `# @create` / `# @update`;本阶段改动在涉及文件头新增一行 `# @update 2026-08-10 <改动说明>`,后续任务均给出该行的精确内容。
- **不引入新依赖**;HTTP API(`/api/v1/*` 与响应模型)保持兼容。
- 部署侧(docker-compose、`.env.example`、docker-readme、`backend/app/core/index.md`/`backend/index.md` 的文档列表)不在本阶段范围,属阶段四文档统一;`setting_manager` 删除的仅为后端进程内无人消费的默认值,compose 注入的环境变量仍会经 `_load_env` 进入 `config`,不产生缺失引用。

---

## 1. 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/app/runtime/utils/serialization.py` | 统一序列化/深拷贝:`safe_deep_copy` + `to_jsonable` |
| `backend/tests/test_serialization.py` | `safe_deep_copy` / `to_jsonable` 单元测试(TDD 驱动) |
| `backend/tests/test_plugin_models.py` | `PluginItem`/`PluginErrorItem.from_info` 工厂测试(TDD 驱动) |

### 修改

| 文件 | 职责 |
|------|------|
| `backend/app/runtime/storage/store.py` | 删除 `_deep_copy_with_ref_tracking`,改用 `safe_deep_copy` |
| `backend/app/runtime/runner/runner.py` | 删除 `_deep_copy_or_str`/`_to_vars_value`,改用 `safe_deep_copy`/`to_jsonable` |
| `backend/app/plugin/models.py` | `PluginItem`/`PluginErrorItem` 增加 `from_info(info)` 类工厂 |
| `backend/app/api/v1/plugins.py` | 推导式收拢为 `from_info` 工厂调用 |
| `backend/app/runtime/plugin_loader.py` | 阶段一基础上的最终收敛(注释/头注释清理,逻辑不变) |
| `backend/tests/test_plugin_loader.py` | 新增文件插件(子目录 .py)模块名解析用例;修正头注释超长与引号注解 |
| `backend/app/core/setting_manager.py` | 删除 DB/Redis 死配置默认值与 `REDIS_URL` 拼接 |
| `backend/app/main.py` | 移除 `env_secrets` 的 import 与调用 |

### 删除

| 文件 |
|------|
| `backend/app/core/env_secrets.py` |

---

## Task 1: 新增 `test_serialization.py`(TDD 红)

**Files:**
- Create: `backend/tests/test_serialization.py`
- Test: `backend/tests/test_serialization.py`

- [ ] **Step 1: 创建 `backend/tests/test_serialization.py`(全文)**

```python
# @file /backend/tests/test_serialization.py
# @brief app.runtime.utils.serialization 单元测试:safe_deep_copy / to_jsonable
# @create 2026-08-10

from __future__ import annotations

from app.runtime.utils.serialization import safe_deep_copy, to_jsonable


class TestSafeDeepCopy:
    def test_deep_copies_nested_dict(self) -> None:
        source = {"a": [1, 2, {"b": 3}]}
        result = safe_deep_copy(source)
        assert result == source
        result["a"][2]["b"] = 99
        assert source["a"][2]["b"] == 3

    def test_handles_self_referencing_list(self) -> None:
        value = [1, 2]
        value.append(value)
        result = safe_deep_copy(value)
        assert result[:2] == [1, 2]
        assert result[2] is result

    def test_handles_shared_references(self) -> None:
        shared = {"x": 1}
        value = {"a": shared, "b": shared}
        result = safe_deep_copy(value)
        assert result["a"] == result["b"] == {"x": 1}
        assert result["a"] is result["b"]

    def test_primitives_returned_as_is(self) -> None:
        assert safe_deep_copy(None) is None
        assert safe_deep_copy(1) == 1
        assert safe_deep_copy("s") == "s"
        assert safe_deep_copy(True) is True

    def test_uncopyable_falls_back_to_str(self) -> None:
        class Uncopyable:
            def __str__(self) -> str:
                return "<uncopyable>"

            def __deepcopy__(self, memo):
                raise TypeError("boom")

        result = safe_deep_copy({"obj": Uncopyable()})
        assert result == {"obj": "<uncopyable>"}


class TestToJsonable:
    def test_passthrough_dict(self) -> None:
        assert to_jsonable({"a": 1, "b": [True, None]}) == {"a": 1, "b": [True, None]}

    def test_non_serializable_uses_default_str(self) -> None:
        class Obj:
            def __str__(self) -> str:
                return "<obj>"

        result = to_jsonable({"obj": Obj(), "n": 1})
        assert result == {"obj": "<obj>", "n": 1}

    def test_circular_reference_returns_str_fallback(self) -> None:
        value = {"name": "x"}
        value["self"] = value
        result = to_jsonable(value)
        assert isinstance(result, str)
        assert "x" in result

    def test_string_fallback_when_dumps_fails(self) -> None:
        class BrokenStr:
            def __str__(self) -> str:
                raise ValueError("no str")

        result = to_jsonable({"x": BrokenStr()})
        assert isinstance(result, str)
```

- [ ] **Step 2: 运行测试,验证失败(红)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_serialization.py -q`
Expected: FAIL at collection, key line:

```
ModuleNotFoundError: No module named 'app.runtime.utils.serialization'
```

---

## Task 2: 实现 `backend/app/runtime/utils/serialization.py`(TDD 绿)并提交

**Files:**
- Create: `backend/app/runtime/utils/serialization.py`
- Test: `backend/tests/test_serialization.py`

- [ ] **Step 1: 创建文件(全文)**

```python
# @file /backend/app/runtime/utils/serialization.py
# @brief 序列化/深拷贝统一工具:引用跟踪打断循环引用,无法序列化的值退化为 str
# @create 2026-08-10

from __future__ import annotations

import copy
import json
from typing import Any


def safe_deep_copy(value: Any) -> Any:
    """深拷贝,引用跟踪打断循环引用;无法拷贝的容器成员退化为 str

    统一替换原 store._deep_copy_with_ref_tracking 与 runner._deep_copy_or_str。
    dict/list 递归拷贝(共享引用保持),基本类型原样返回,
    其余对象经 copy.deepcopy,失败时退化为 str(value)。
    """
    seen: dict[int, Any] = {}

    def _copy(obj: Any) -> Any:
        obj_id = id(obj)
        if obj_id in seen:
            return seen[obj_id]

        if isinstance(obj, dict):
            result: dict[Any, Any] = {}
            seen[obj_id] = result
            for k, v in obj.items():
                result[k] = _copy(v)
            return result

        if isinstance(obj, list):
            result: list[Any] = []
            seen[obj_id] = result
            for item in obj:
                result.append(_copy(item))
            return result

        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        try:
            return copy.deepcopy(obj)
        except Exception:
            return str(obj)

    return _copy(value)


def to_jsonable(value: Any) -> Any:
    """JSON 往返打断循环引用,无法序列化的值经 default=str 处理

    统一替换 runner._to_vars_value。dumps 整体失败时退化为 str(value)。
    """
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)
```

> 说明:`safe_deep_copy` 的递归引用跟踪同时兼容原 store 版(带 seen 参数打断循环)与原 runner 版(`copy.deepcopy` + str 兜底);对普通 dict/list/基本类型/任意对象,两者结果一致,引用跟踪还额外处理了循环引用场景,故为行为超集。store 与 runner 均直接从子模块引入(`from app.runtime.utils.serialization import safe_deep_copy` 或 `to_jsonable`),与现有 `output_externalizer` 的引入方式一致,不修改 `app/runtime/utils/__init__.py`。

- [ ] **Step 2: 运行测试,验证通过(绿)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_serialization.py -q`
Expected: PASS, key line:

```
9 passed
```

- [ ] **Step 3: ruff 校验本任务文件**

> 说明:此处仅校验本任务涉及的两个文件。阶段一遗留的 `tests/test_plugin_loader.py` 存在 E501/UP037 类 lint 问题,须待 Task 7 重写该文件后才能对 `tests` 全量跑 ruff。

Run: `cd backend && .venv/bin/ruff check app/runtime/utils/serialization.py tests/test_serialization.py && .venv/bin/ruff format --check app/runtime/utils/serialization.py tests/test_serialization.py`
Expected: `All checks passed!` 与 `N files already formatted`(exit code 0)

- [ ] **Step 4: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/runtime/utils/serialization.py backend/tests/test_serialization.py
git commit -m "refactor(backend): add unified serialization utils (safe_deep_copy / to_jsonable)"
```

---

## Task 3: `store.py` 切换到 `safe_deep_copy`

**Files:**
- Modify: `backend/app/runtime/storage/store.py`

- [ ] **Step 1: 删除 `_deep_copy_with_ref_tracking` 并更新 import 与头注释**

将 store.py 顶部(第 1–45 行)由「原样」替换为「新样」:

原样:

```python
# @file /backend/app/runtime/storage/store.py
# @brief 运行记录的最小存储（内存 + 产物落盘）
# @create 2026-02-21 00:00:00
# @update 2026-03-15 修复循环引用导致的序列化问题

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

from app.runtime.models import RunResult


def _deep_copy_with_ref_tracking(obj: Any, seen: dict[int, Any] | None = None) -> Any:
    if seen is None:
        seen = {}

    obj_id = id(obj)
    if obj_id in seen:
        return seen[obj_id]

    if isinstance(obj, dict):
        result = {}
        seen[obj_id] = result
        for k, v in obj.items():
            result[k] = _deep_copy_with_ref_tracking(v, seen)
        return result

    if isinstance(obj, list):
        result = []
        seen[obj_id] = result
        for item in obj:
            result.append(_deep_copy_with_ref_tracking(item, seen))
        return result

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    try:
        return copy.deepcopy(obj)
    except Exception:
        return str(obj)
```

新样:

```python
# @file /backend/app/runtime/storage/store.py
# @brief 运行记录的最小存储（内存 + 产物落盘）
# @create 2026-02-21 00:00:00
# @update 2026-03-15 修复循环引用导致的序列化问题
# @update 2026-08-10 序列化收敛至 app.runtime.utils.serialization.safe_deep_copy

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.runtime.models import RunResult
from app.runtime.utils.serialization import safe_deep_copy
```

> 说明:`import copy` 在 store.py 仅被被删函数使用,一并移除;`import json` 仍被 `_write_run_artifact` 使用,保留。

- [ ] **Step 2: 更新 `_write_run_artifact` 调用点**

将:

```python
        data = _deep_copy_with_ref_tracking(run.model_dump(mode="python"))
```

替换为:

```python
        data = safe_deep_copy(run.model_dump(mode="python"))
```

- [ ] **Step 3: ruff 校验本任务文件**

Run: `cd backend && .venv/bin/ruff check app/runtime/storage/store.py && .venv/bin/ruff format --check app/runtime/storage/store.py`
Expected: `All checks passed!` 与 `1 file already formatted`(exit code 0)

- [ ] **Step 4: 运行全量测试,验证行为不变**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
92 passed
```

> `92 = 83 + 9`(新增 test_serialization)。`test_foreach.py`/`test_minimal_loop.py` 等现有用例覆盖 store 产物落盘与 runner 行为,作为回归保障。

- [ ] **Step 5: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/runtime/storage/store.py
git commit -m "refactor(backend): use safe_deep_copy in RunStore artifact writing"
```

---

## Task 4: `runner.py` 切换到 `safe_deep_copy` / `to_jsonable`

**Files:**
- Modify: `backend/app/runtime/runner/runner.py`

- [ ] **Step 1: 更新头注释与 import(删除 `import json`,新增 serialization import)**

将 runner.py 顶部(第 1–22 行)由「原样」替换为「新样」:

原样:

```python
# @file /backend/app/runtime/runner/runner.py
# @brief Flow 执行器
# @create 2026-02-21 00:00:00
# @update 2026-03-15 拆分条件与模板解析到独立模块
# @update 2026-08-08 合并 for_each 与普通步骤双路径,修复 duration_ms / check_passed

from __future__ import annotations

import copy
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry
from app.runtime.models import FlowSpec, HookSpec, RunResult, StepResult, StepSpec
from app.runtime.storage.store import RunStore
from app.runtime.utils import evaluate_condition, resolve_templates
from app.runtime.utils.output_externalizer import externalize_if_large
```

新样:

```python
# @file /backend/app/runtime/runner/runner.py
# @brief Flow 执行器
# @create 2026-02-21 00:00:00
# @update 2026-03-15 拆分条件与模板解析到独立模块
# @update 2026-08-08 合并 for_each 与普通步骤双路径,修复 duration_ms / check_passed
# @update 2026-08-10 序列化函数收敛至 app.runtime.utils.serialization

from __future__ import annotations

import copy
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext, CheckContext, Registry
from app.runtime.models import FlowSpec, HookSpec, RunResult, StepResult, StepSpec
from app.runtime.storage.store import RunStore
from app.runtime.utils import evaluate_condition, resolve_templates
from app.runtime.utils.output_externalizer import externalize_if_large
from app.runtime.utils.serialization import safe_deep_copy, to_jsonable
```

> 说明:`import copy` 保留(`run_flow` 中 `copy.deepcopy(dict(vars or {}))` 仍在用);`import json` 仅被删除的 `_to_vars_value` 使用,一并移除。

- [ ] **Step 2: 删除 `_to_vars_value` 与 `_deep_copy_or_str` 两个模块级函数**

将「原样」块(第 31–43 行,含其后空行):

```python
def _to_vars_value(value: Any) -> Any:
    """将 action 输出转为可存入 runtime_vars 的值(JSON 往返打断循环引用)"""
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


def _deep_copy_or_str(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:
        return str(value)


```

整块删除(`class Runner` 直接跟在 `def _utc_now()` 之后)。

- [ ] **Step 3: 更新三处调用点**

3a. 将:

```python
                        "output": _deep_copy_or_str(iter_output),
```

替换为:

```python
                        "output": safe_deep_copy(iter_output),
```

3b. 将:

```python
                        "vars_snapshot": _deep_copy_or_str(runtime_vars_clean),
```

替换为:

```python
                        "vars_snapshot": safe_deep_copy(runtime_vars_clean),
```

3c. 将:

```python
                runtime_vars[step.output_var] = _to_vars_value(action_output)
```

替换为:

```python
                runtime_vars[step.output_var] = to_jsonable(action_output)
```

- [ ] **Step 4: 运行全量测试,验证行为不变**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
92 passed
```

> `test_foreach.py`(iterations 的 `output`/`vars_snapshot` 断言)、`test_minimal_loop.py`/`test_variable_resolution.py`(output_var 变量传递断言)为本次替换的回归保障。

- [ ] **Step 5: ruff 校验本任务文件**

Run: `cd backend && .venv/bin/ruff check app/runtime/runner/runner.py && .venv/bin/ruff format --check app/runtime/runner/runner.py`
Expected: `All checks passed!` 与 `1 file already formatted`(exit code 0)

- [ ] **Step 6: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/runtime/runner/runner.py
git commit -m "refactor(backend): use safe_deep_copy / to_jsonable in Runner"
```

---

## Task 5: 新增 `test_plugin_models.py`(TDD 红)

**Files:**
- Create: `backend/tests/test_plugin_models.py`
- Test: `backend/tests/test_plugin_models.py`

- [ ] **Step 1: 创建 `backend/tests/test_plugin_models.py`(全文)**

```python
# @file /backend/tests/test_plugin_models.py
# @brief PluginItem / PluginErrorItem from_info 工厂方法测试
# @create 2026-08-10

from __future__ import annotations

from app.core.registry import PluginInfo, PluginLoadErrorInfo
from app.plugin.models import PluginErrorItem, PluginItem


def test_plugin_item_from_info() -> None:
    item = PluginItem.from_info(PluginInfo(name="dummy", version="0.1.0"))
    assert item.name == "dummy"
    assert item.version == "0.1.0"


def test_plugin_error_item_from_info() -> None:
    info = PluginLoadErrorInfo(plugin_id="p1", file_path="/tmp/x.py", error="boom")
    item = PluginErrorItem.from_info(info)
    assert item.plugin_id == "p1"
    assert item.file_path == "/tmp/x.py"
    assert item.error == "boom"
```

- [ ] **Step 2: 运行测试,验证失败(红)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_models.py -q`
Expected: FAIL, key line:

```
FAILED tests/test_plugin_models.py::test_plugin_item_from_info - AttributeError: type object 'PluginItem' has no attribute 'from_info'
```

---

## Task 6: 实现 `from_info` 工厂并收拢 `plugins.py`(TDD 绿)并提交

**Files:**
- Modify: `backend/app/plugin/models.py`
- Modify: `backend/app/api/v1/plugins.py`
- Test: `backend/tests/test_plugin_models.py`

- [ ] **Step 1: 修改 `backend/app/plugin/models.py`(全文替换)**

原样:

```python
# @file /backend/app/plugin/models.py
# @brief 插件相关的 Pydantic 模型
# @create 2026-02-21 00:00:00

from __future__ import annotations

from pydantic import BaseModel


class PluginItem(BaseModel):
    name: str
    version: str


class PluginErrorItem(BaseModel):
    plugin_id: str
    file_path: str
    error: str


class PluginsResponse(BaseModel):
    plugins: list[PluginItem]
    actions: list[str]
    checks: list[str]
    errors: list[PluginErrorItem]
```

新样:

```python
# @file /backend/app/plugin/models.py
# @brief 插件相关的 Pydantic 模型
# @create 2026-02-21 00:00:00
# @update 2026-08-10 新增 from_info 工厂方法,收敛 api 层映射样板

from __future__ import annotations

from app.core.registry import PluginInfo, PluginLoadErrorInfo
from pydantic import BaseModel


class PluginItem(BaseModel):
    name: str
    version: str

    @classmethod
    def from_info(cls, info: PluginInfo) -> PluginItem:
        """从 registry.PluginInfo 构造"""
        return cls(name=info.name, version=info.version)


class PluginErrorItem(BaseModel):
    plugin_id: str
    file_path: str
    error: str

    @classmethod
    def from_info(cls, info: PluginLoadErrorInfo) -> PluginErrorItem:
        """从 registry.PluginLoadErrorInfo 构造"""
        return cls(
            plugin_id=info.plugin_id,
            file_path=info.file_path,
            error=info.error,
        )


class PluginsResponse(BaseModel):
    plugins: list[PluginItem]
    actions: list[str]
    checks: list[str]
    errors: list[PluginErrorItem]
```

> 说明:import 顺序为 `app`(first-party)在 `pydantic`(third-party)之前,与仓库现有 `app/main.py`、`app/api/v1/runs.py` 的 ruff isort 约定一致(本计划内容已经 ruff 0.16.2 实测通过)。`-> PluginItem` 无需引号:`from __future__ import annotations` 下注解为惰性字符串(ruff UP037 要求)。`app.plugin.models` → `app.core.registry` 无循环依赖(registry 仅依赖 stdlib)。

- [ ] **Step 2: 修改 `backend/app/api/v1/plugins.py` 的映射推导式**

将:

```python
    plugins = [
        PluginItem(name=p.name, version=p.version) for p in registry.list_plugins()
    ]
    errors = [
        PluginErrorItem(plugin_id=e.plugin_id, file_path=e.file_path, error=e.error)
        for e in registry.list_plugin_errors()
    ]
```

替换为:

```python
    plugins = [PluginItem.from_info(p) for p in registry.list_plugins()]
    errors = [PluginErrorItem.from_info(e) for e in registry.list_plugin_errors()]
```

并在文件头 `# @create` 后新增一行:

```python
# @update 2026-08-10 映射收敛为 from_info 工厂调用
```

- [ ] **Step 3: 运行测试,验证通过(绿)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_models.py -q`
Expected: PASS, key line:

```
2 passed
```

- [ ] **Step 4: 运行全量测试(含 API 回归)**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
94 passed
```

> `94 = 92 + 2`。`test_minimal_loop.py`(GET /api/v1/plugins 断言 `dummy.echo` 在 actions 中)与 `test_foreach.py` 为 plugins.py 收拢后的 API 回归保障。

- [ ] **Step 5: ruff 校验本任务文件**

Run: `cd backend && .venv/bin/ruff check app/plugin/models.py app/api/v1/plugins.py tests/test_plugin_models.py && .venv/bin/ruff format --check app/plugin/models.py app/api/v1/plugins.py tests/test_plugin_models.py`
Expected: `All checks passed!` 与 `3 files already formatted`(exit code 0)

- [ ] **Step 6: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/plugin/models.py backend/app/api/v1/plugins.py backend/tests/test_plugin_models.py
git commit -m "refactor(backend): add PluginItem/PluginErrorItem from_info factories"
```

---

## Task 7: `plugin_loader.py` 最终收敛 + 文件插件用例补强

**Files:**
- Modify: `backend/app/runtime/plugin_loader.py`(全文重写为最终形态)
- Modify: `backend/tests/test_plugin_loader.py`(全文重写:修正头注释/注解,新增文件插件用例)

> 前置说明:阶段一已完成 PLUGIN 识别、config 注入、`plugin.register` 调用、register 协议删除、目录/文件模块名解析保留、失败上报不变。本任务将 loader 收敛为最终形态(头注释更新、注释与 docstring 统一为中文、去掉「阶段一/阶段二」过渡措辞),**逻辑零改动**;并补齐「文件插件(子目录 .py)模块名解析」用例(阶段一用例仅覆盖目录插件)。同时,阶段一版本 `tests/test_plugin_loader.py` 的头注释超长(E501)与 `instances` 注解引号(UP037)在本任务重写中一并修正——因此**全量 ruff 自本任务起才可对 `tests` 全量通过**。

- [ ] **Step 1: 重写 `backend/app/runtime/plugin_loader.py`(全文)**

```python
# @file /backend/app/runtime/plugin_loader.py
# @brief 插件加载器 - 读取 plugins.yaml 启用的插件并注册到 Registry
# @create 2026-08-08
# @update 2026-08-10 阶段二:收敛为 PLUGIN (Plugin 子类) 协议最终形态

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
    """读取 plugins.yaml,返回 {plugin_key: {path}} 启用的插件条目"""
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
    """加载插件目录下 config.yaml 并解析 secrets(环境变量值)

    无 config.yaml 时返回 None;secrets 块逐项按环境变量解析。
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
    """加载 plugins.yaml 中启用的插件,识别 PLUGIN (Plugin 子类) 完成注册

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

            # 模块名取解析后路径的目录名/文件名,与 plugins.yaml 的 key 解耦;
            # 文件插件取相对 plugins_dir 的路径(去 .py 后缀、分隔符转点号),
            # 例如 plugins/examples/hello_world.py → plugins.examples.hello_world
            if path.is_dir():
                module_name = path.name
            else:
                rel = path.resolve().relative_to(plugins_dir.resolve())
                module_name = (
                    str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
                )
            module = importlib.import_module(f"plugins.{module_name}")

            plugin_cls = getattr(module, "PLUGIN", None)
            if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, Plugin)):
                raise AttributeError(
                    f"插件模块 {module_name} 未暴露 PLUGIN (Plugin 子类)"
                )

            # config.yaml 仅对目录插件加载,文件插件传入 None
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

- [ ] **Step 2: 重写 `backend/tests/test_plugin_loader.py`(全文,11 个用例)**

> 相对阶段一版本的变化:@brief 头注释缩短以修复 E501 超长;`instances` 注解去掉引号(ruff UP037);新增 `test_loads_file_plugin_with_subdirectory_module_name`(文件插件模块名解析用例)。

```python
# @file /backend/tests/test_plugin_loader.py
# @brief Tests for plugin_loader: YAML/config 解析、PLUGIN (Plugin 子类) 加载
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
    instances: list[_RecordingPlugin] = []

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

    def test_loads_file_plugin_with_subdirectory_module_name(
        self, monkeypatch, tmp_path: Path
    ):
        """文件插件:模块名解析为相对路径点号形式(目录/文件形态保留),config 为 None。"""
        _RecordingPlugin.instances.clear()
        registry = Registry()
        plugins_dir = tmp_path / "plugins"
        file_plugin = plugins_dir / "examples" / "hello_world.py"
        file_plugin.parent.mkdir(parents=True)
        file_plugin.write_text("", encoding="utf-8")

        mock_module = MagicMock()
        mock_module.PLUGIN = _RecordingPlugin

        monkeypatch.setattr(
            "app.runtime.plugin_loader._plugins_dir",
            lambda: plugins_dir,
        )
        monkeypatch.setattr(
            "app.runtime.plugin_loader._load_registry_entries",
            lambda _: {"hello": {"path": file_plugin}},
        )
        imported_names: list[str] = []

        def _fake_import(name: str):
            imported_names.append(name)
            return mock_module

        monkeypatch.setattr(
            "app.runtime.plugin_loader.importlib.import_module",
            _fake_import,
        )

        load_plugins(registry)

        assert imported_names == ["plugins.examples.hello_world"]
        assert len(_RecordingPlugin.instances) == 1
        assert _RecordingPlugin.instances[0].received_config is None
        assert [(p.name, p.version) for p in registry.list_plugins()] == [
            ("test-plugin", "9.9.9")
        ]
```

- [ ] **Step 3: 运行 loader 测试,验证通过**

Run: `cd backend && .venv/bin/python -m pytest tests/test_plugin_loader.py -q`
Expected: PASS, key line:

```
11 passed
```

- [ ] **Step 4: 运行全量测试与 ruff**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
95 passed
```

Run: `cd backend && .venv/bin/ruff check app tests ../plugins && .venv/bin/ruff format --check app tests ../plugins`
Expected: `All checks passed!` 与 `N files already formatted`(exit code 0)

- [ ] **Step 5: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/runtime/plugin_loader.py backend/tests/test_plugin_loader.py
git commit -m "refactor(backend): converge plugin_loader to final PLUGIN protocol form"
```

---

## Task 8: `setting_manager.py` 删除 DB/Redis 死配置

**Files:**
- Modify: `backend/app/core/setting_manager.py`

- [ ] **Step 1: grep 确认无引用**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "DB_HOST\|DB_PORT\|DB_USER\|DB_NAME\|DB_PASSWORD\|REDIS_HOST\|REDIS_PORT\|REDIS_DB\|REDIS_URL\|SECRET_KEY" backend/app --include="*.py"`
Expected: 命中**仅**出现在 `backend/app/core/setting_manager.py` 与 `backend/app/core/env_secrets.py` 两个文件(即除待删配置本身与其 allowlist 外无任何消费者);若出现第三个文件,先停下来核查引用来源再继续。

- [ ] **Step 2: 修改 `backend/app/core/setting_manager.py`**

2a. 头注释 `# @create` 后新增一行:

```python
# @update 2026-08-10 删除未被引用的 DB/Redis 死配置
```

2b. 将「原样」块(第 51–65 行):

```python
        self.config.setdefault("DB_EXTERNAL_PORT", 3306)
        self.config.setdefault("REDIS_EXTERNAL_PORT", 6379)
        self.config.setdefault("LOG_LEVEL", "INFO")
        self.config.setdefault("DB_USER", "autoflow")
        self.config.setdefault("DB_NAME", "autoflow_db")
        self.config.setdefault("REDIS_DB", 0)
        self.config.setdefault("SERVE_STATIC_FILES", "False")
        self.config.setdefault("STATIC_FILES_DIR", "/app/static")
        self.config.setdefault("CORS_ORIGINS", os.getenv("CORS_ORIGINS", "*"))
        self.config.setdefault("DB_HOST", "mysql")
        self.config.setdefault("DB_PORT", 3306)
        self.config.setdefault("REDIS_HOST", "redis")
        self.config.setdefault("REDIS_PORT", 6379)
        self.config.setdefault("DB_PASSWORD", "")
        self.config.setdefault("SECRET_KEY", "")
```

替换为「新样」:

```python
        self.config.setdefault("LOG_LEVEL", "INFO")
        self.config.setdefault("SERVE_STATIC_FILES", "False")
        self.config.setdefault("STATIC_FILES_DIR", "/app/static")
        self.config.setdefault("CORS_ORIGINS", os.getenv("CORS_ORIGINS", "*"))
```

2c. 将「原样」块(第 70–73 行):

```python
        self.config["API_V1_STR"] = f"/api/{self.config['API_VERSION']}"
        self.config["REDIS_URL"] = (
            f"redis://{self.config['REDIS_HOST']}:{self.config['REDIS_PORT']}/{self.config['REDIS_DB']}"
        )
        self.config["PORT"] = int(
```

替换为「新样」:

```python
        self.config["API_V1_STR"] = f"/api/{self.config['API_VERSION']}"
        self.config["PORT"] = int(
```

> 说明:保留 BACKEND_*/FRONTEND_* 端口(docker-compose 与 scripts/start.sh 使用)及 LOG_LEVEL/SERVE_STATIC_FILES/STATIC_FILES_DIR/CORS_ORIGINS 等被 `app/main.py` 消费的配置;删除的 DB_HOST/DB_PORT/DB_USER/DB_NAME/DB_PASSWORD/REDIS_HOST/REDIS_PORT/REDIS_DB/SECRET_KEY/DB_EXTERNAL_PORT/REDIS_EXTERNAL_PORT 均无后端代码消费(compose 注入的环境变量仍会经 `_load_env` 原样进入 config,不产生缺失引用)。

- [ ] **Step 3: ruff 校验本任务文件**

Run: `cd backend && .venv/bin/ruff check app/core/setting_manager.py && .venv/bin/ruff format --check app/core/setting_manager.py`
Expected: `All checks passed!` 与 `1 file already formatted`(exit code 0)

- [ ] **Step 4: 运行全量测试,验证无回归**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
95 passed
```

- [ ] **Step 5: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add backend/app/core/setting_manager.py
git commit -m "refactor(backend): remove dead DB/Redis config from setting_manager"
```

---

## Task 9: 删除 `env_secrets.py` 死代码

**Files:**
- Delete: `backend/app/core/env_secrets.py`
- Modify: `backend/app/main.py`

> 设计说明:env_secrets 的 allowlist(`DB_PASSWORD_FILE`/`SECRET_KEY_FILE`/`MYSQL_ROOT_PASSWORD_FILE`)写入的 `DB_PASSWORD`/`SECRET_KEY`/`MYSQL_ROOT_PASSWORD` 在后端代码中无任何消费(Stage 1 已确认仅 setting_manager 默认值与 allowlist 自身引用它们,且 setting_manager 默认值已在 Task 8 删除)。allowlist 同步核对结果为「实际使用的 secret 为空」,按 spec 4.4「仅保留实际使用的 secret」,allowlist 清空后函数退化为 no-op,属死代码,一并删除。docker-compose 向容器注入的 `*_FILE` 环境变量不被消费即无害;部署文档(docker-readme、compose)归阶段四统一。

- [ ] **Step 1: grep 确认三个 secret 无后端消费者**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "DB_PASSWORD\|SECRET_KEY\|MYSQL_ROOT_PASSWORD" backend/app --include="*.py"`
Expected: 命中**仅**在 `backend/app/core/env_secrets.py`(allowlist 自身);若出现其他文件,先停下来核查。

- [ ] **Step 2: 删除 `backend/app/core/env_secrets.py` 并清理 `main.py` 调用**

2a. 删除文件:

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
rm backend/app/core/env_secrets.py
```

2b. `backend/app/main.py` import 处,将:

```python
from app.api import register_routers
from app.core.env_secrets import apply_file_env
from app.core.setting_manager import setting_manager
```

替换为:

```python
from app.api import register_routers
from app.core.setting_manager import setting_manager
```

2c. `backend/app/main.py` 的 `init_services` 中,将:

```python
def init_services():
    """初始化所有服务"""
    global _services_initialized
    if _services_initialized:
        return
    apply_file_env()
    args = parse_args()
    setting_manager.init(args)
    _services_initialized = True
```

替换为:

```python
def init_services():
    """初始化所有服务"""
    global _services_initialized
    if _services_initialized:
        return
    args = parse_args()
    setting_manager.init(args)
    _services_initialized = True
```

2d. `backend/app/main.py` 头注释 `# @create` 后新增一行:

```python
# @update 2026-08-10 移除 env_secrets 文件密钥注入(allowlist 为空,属死代码)
```

- [ ] **Step 3: ruff 校验本任务文件**

Run: `cd backend && .venv/bin/ruff check app/main.py && .venv/bin/ruff format --check app/main.py`
Expected: `All checks passed!` 与 `1 file already formatted`(exit code 0)

- [ ] **Step 4: 运行全量测试**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
95 passed
```

> `test_foreach.py`/`test_minimal_loop.py` 等导入 `app.main` 的用例覆盖 `init_services` 启动路径,证明移除调用后应用正常初始化。

- [ ] **Step 5: /health 冒烟(显式验证应用启动路径)**

Run: `cd backend && .venv/bin/python -c "
from fastapi.testclient import TestClient
from app.main import app
resp = TestClient(app).get('/health')
assert resp.status_code == 200 and resp.json() == {'status': 'healthy'}
print('health OK')"`
Expected: `health OK`

- [ ] **Step 6: 提交**

```bash
cd /home/mcocdaa/AI_CODE/AutoFlow
git add -A backend/app/core backend/app/main.py
git commit -m "refactor(backend): remove dead env_secrets file secret handling"
```

---

## Task 10: 最终验收

**Files:**
- 验证 spec 第 4.5 节与第 8 章全部验收项(无需新代码)

- [ ] **Step 1: grep 验收——后端无重复序列化函数**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "_deep_copy_with_ref_tracking\|_deep_copy_or_str\|_to_vars_value" backend/app --include="*.py"`
Expected: 无输出(exit code 1),三处旧函数零残留。

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "def safe_deep_copy\|def to_jsonable" backend/app --include="*.py"`
Expected: 仅 `backend/app/runtime/utils/serialization.py` 两处定义:

```
backend/app/runtime/utils/serialization.py:12:def safe_deep_copy(value: Any) -> Any:
backend/app/runtime/utils/serialization.py:51:def to_jsonable(value: Any) -> Any:
```

- [ ] **Step 2: grep 验收——DB/Redis 死配置与 env_secrets 零残留**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && grep -rn "REDIS_URL\|DB_HOST\|SECRET_KEY\|apply_file_env" backend/app --include="*.py"`
Expected: 无输出(exit code 1)。

- [ ] **Step 3: ruff 检查**

Run: `cd backend && .venv/bin/ruff check app tests ../plugins && .venv/bin/ruff format --check app tests ../plugins`
Expected: `All checks passed!` 与 `N files already formatted`(exit code 0)

- [ ] **Step 4: 全量 pytest**

Run: `cd backend && .venv/bin/python -m pytest tests ../plugins/zhihu_digest/tests ../plugins/desktop_checkin/tests -q`
Expected: PASS, key line:

```
95 passed
```

- [ ] **Step 5: 启动冒烟——/health、/plugins、/runs/execute**

Run: `cd backend && .venv/bin/python - <<'EOF'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

resp = client.get("/health")
assert resp.status_code == 200 and resp.json() == {"status": "healthy"}
print("health:", resp.json())

resp = client.get("/api/v1/plugins")
assert resp.status_code == 200
data = resp.json()
print("plugins:", [p["name"] for p in data["plugins"]])
assert len(data["plugins"]) == 6, data
assert {p["name"] for p in data["plugins"]} == {
    "builtin", "dummy", "openclaw", "ai-deepseek", "zhihu-digest", "desktop-checkin",
}, data
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
print("OK: health + 6 plugins + smoke run success")
EOF`
Expected: key lines:

```
health: {'status': 'healthy'}
plugins: ['builtin', 'dummy', 'openclaw', 'ai-deepseek', 'zhihu-digest', 'desktop-checkin']
run status: success
OK: health + 6 plugins + smoke run success
```

> 冒烟同时验证「配置日志无缺失引用」:TestClient 导入 `app.main` 会执行 `init_services()`(含 `_log_config`),上述输出无异常即代表移除 DB/Redis 配置后无缺失引用。

- [ ] **Step 6: 冒烟后检查 git 状态干净(无未提交改动)**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && git status --short`
Expected: 无输出(工作区干净)

---

## 2. 验收汇总(对应 spec 第 4 章与第 8 章)

| 验收项 | 验证任务 |
|--------|----------|
| `safe_deep_copy`/`to_jsonable` 单测 9 个,store/runner 行为由现有测试回归 | Task 1、Task 2、Task 3、Task 4 |
| 后端无重复序列化函数:`grep _deep_copy` 仅剩 serialization.py 一处定义 | Task 10 Step 1 |
| `PluginItem`/`PluginErrorItem.from_info` 工厂 + `api/v1/plugins.py` 收拢 | Task 5、Task 6(2 个单测 + 全量回归) |
| loader 收敛为 PLUGIN 协议最终形态;register 协议已删;目录/文件模块名解析保留;失败上报不变 | Task 7(loader 逻辑零改动,11 个 loader 用例含新增文件插件用例) |
| `setting_manager` DB/Redis 死配置与 `REDIS_URL` 拼接删除;端口配置(BACKEND_*/FRONTEND_*)保留 | Task 8(grep 确认无引用 + 全量回归) |
| `env_secrets` allowlist 核对后清理(无实际使用的 secret) | Task 9 |
| 全部 pytest 通过 | Task 10 Step 4(`95 passed`) |
| ruff 通过 | Task 10 Step 3 |
| `/health`、`/plugins`、`/runs/execute` 冒烟正常,配置日志无缺失引用 | Task 10 Step 5、Task 9 Step 5 |
| 每个任务独立 commit,`refactor(backend):` 前缀 | Task 2–9 提交步骤 |
