---
title: Plugin Development Guide
description: Plugin development guide for the Plugin base class ABI
keywords: [plugin, guide, sdk, development]
version: "2.0"
---

# AutoFlow Plugin Development Guide

This guide covers plugin development for AutoFlow using the `Plugin` base class ABI. It is aimed at team developers; reading it end-to-end covers the core concepts.

## Table of Contents

- [1. Quick Start](#1-quick-start)
- [2. The Plugin Base Class](#2-the-plugin-base-class)
- [3. Action Development](#3-action-development)
- [4. Check Development](#4-check-development)
- [5. Shared Helpers (plugins/common/helpers.py)](#5-shared-helpers-pluginscommonhelperspy)
- [6. Configuration & Secrets (config.yaml)](#6-configuration--secrets-configyaml)
- [7. Registry & Loading](#7-registry--loading)
- [8. Example Analysis](#8-example-analysis)

## 1. Quick Start

### Minimal Plugin Layout

Every AutoFlow plugin is a directory (or a single `.py` file) containing:

```
plugin_dir/
├── __init__.py       # package entry (exports PLUGIN)
├── backend.py        # class XxxPlugin(Plugin); actions/checks declared as class attributes
└── config.yaml       # optional; defaults + secrets (secrets resolved to env values by the loader)
```

Directory plugins must contain `__init__.py` and are imported by `backend/app/runtime/plugin_loader.py` as `plugins.<dir_name>`. File plugins (e.g. `plugins/examples/*.py`) define the `Plugin` subclass and export `PLUGIN` in a single file.

### Complete Minimal Example

See `plugins/dummy/backend.py`:

```python
# @file /plugins/dummy/backend.py
# @brief Dummy plugin: echoes user input (for testing)

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
    """Dummy plugin: echoes user input (for testing)"""

    name = "dummy"
    version = "0.1.0"
    actions = {
        "dummy.echo": _echo,
    }
    checks = {}


PLUGIN = DummyPlugin
```

`__init__.py` only exports `PLUGIN`:

```python
# @file /plugins/dummy/__init__.py
# @brief Dummy plugin entry

from plugins.dummy.backend import PLUGIN

__all__ = ["PLUGIN"]
```

Register the plugin in `plugins/plugins.yaml` to load it:

```yaml
plugins:
  dummy:
    enabled: true
```

## 2. The Plugin Base Class

`Plugin` lives in `plugins/common/plugin.py` and provides declarative metadata plus unified registration (replacing the old hooks.py boilerplate):

```python
class Plugin:
    """Plugin base: declarative metadata + unified registration"""

    name: str
    version: str = "0.1.0"
    actions: dict[str, ActionHandler] = {}
    checks: dict[str, CheckHandler] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def register(self, registry: Registry) -> None:
        """Register plugin metadata, actions and checks"""
        registry.register_plugin(self.name, self.version)
        for type_name, handler in self.actions.items():
            registry.register_action(type_name, handler)
        for type_name, handler in self.checks.items():
            registry.register_check(type_name, handler)
```

Key rules:

- **`name`**: unique plugin identifier, decoupled from the plugins.yaml key (but keeping them consistent is recommended).
- **`version`**: plugin version, defaults to `"0.1.0"`.
- **`actions` / `checks`**: declared as **class attributes** mapping `type_name -> handler`. Handlers must be **module-level functions or `@staticmethod`** (instance methods cannot be referenced inside the class body).
- **`__init__(config)`**: the loader injects the parsed `config.yaml` (or `None` when absent); plugins read `defaults` / `secrets` here.
- **`register()`**: implemented by the base class — plugins never write it.
- **`PLUGIN = XxxPlugin`**: modules must export `PLUGIN` (a class reference, not an instance); the loader discovers plugins through it.

Type names follow `plugin_name.function`, e.g. `zhihu.fetch_answer`, `desktop.click`.

## 3. Action Development

### ActionHandler Signature

```python
ActionHandler = Callable[[ActionContext, dict[str, Any]], Any]
```

- `ActionContext`: contextual information (below)
- `dict[str, Any]`: parameters (the `params` section of a Flow step, already template-resolved)
- Return value: any data structure (becomes the next step's `input`)

### ActionContext Fields

```python
@dataclass(frozen=True)
class ActionContext:
    run_id: str              # run ID
    step_id: str             # step ID
    input: Any | None        # previous step's input
    vars: dict[str, Any]     # variables dictionary
    artifacts_dir: Path      # artifacts directory
```

Commonly used:

- `input`: data from the previous step
- `vars`: global variables, e.g. configuration
- `artifacts_dir`: directory for artifacts; create subdirectories here

### Return Value

The return value is unconstrained, but a dict with key info is recommended:

```python
return {
    "result": True,           # execution result
    "data": processed_data,   # concrete data
    "message": "success",     # human-readable message
    "dry_run": False,         # whether simulation mode (optional)
}
```

### Parameter Validation & Errors

- Raise `ValueError("xxx is required")` for missing required params; the Runner converts the exception into a step failure with the error recorded.
- Read optional params with `params.get("key", default)`.

## 4. Check Development

### CheckHandler Signature

```python
CheckHandler = Callable[[CheckContext, dict[str, Any]], bool]
```

- `CheckContext`: contextual information (below)
- `dict[str, Any]`: check parameters
- Return value: `True` / `False` for the check result

### CheckContext Fields

```python
@dataclass(frozen=True)
class CheckContext:
    run_id: str               # run ID
    step_id: str              # step ID
    action_output: Any | None # previous action output
    vars: dict[str, Any]      # variables dictionary
```

Commonly used:

- `action_output`: the previous action's return value; base checks on it
- `vars`: global variables

### Returning True/False

```python
return True   # check passed
return False  # check failed
```

A failed check marks the step as failed; no exception is needed.

## 5. Shared Helpers (plugins/common/helpers.py)

Common utilities are centralized in `plugins/common/helpers.py`. Reuse them — do not copy-paste:

| Function | Description |
|----------|-------------|
| `is_truthy(v)` | Lenient truthiness: `None`/empty are False; `"1"/"true"/"yes"` etc. are True |
| `dry_run_enabled(ctx, params, env_var)` | Three-level dry-run check: `params` → `ctx.vars` → env var |
| `read_text(ctx, path, extra_roots=())` | Safe path read (path-traversal guard; allows artifacts_dir and repo root by default) |
| `write_text(ctx, rel_path, text)` | Write into artifacts_dir; returns the relative path |
| `utc_now_iso()` | UTC ISO 8601 timestamp string |
| `safe_name(name, fallback)` | Filename sanitization (strips separators and illegal chars) |

### Dry-run Example

See `plugins/zhihu_digest/backend.py`:

```python
from plugins.common.helpers import dry_run_enabled

_DRY_RUN_ENV = "AUTOFLOW_ZHIHU_DRY_RUN"

def _fetch_answer(ctx: ActionContext, params: dict[str, Any]) -> Any:
    ...
    if dry_run_enabled(ctx, params, _DRY_RUN_ENV):
        # simulation path: no real request, return sample data
        rel = write_text(ctx, f"zhihu/answers/{answer_id}.txt", "sample text")
        return {"answer_text_path": rel, "dry_run": True}
    # real path
    ...
```

Precedence: `dry_run` in `params` → `dry_run` in `ctx.vars` → plugin-specific env var (convention `AUTOFLOW_<PLUGIN>_DRY_RUN`).

### Safe Path I/O Example

See `plugins/ai_deepseek/backend.py`:

```python
from plugins.common.helpers import read_text, write_text

# write into artifacts dir, returns relative path
summary_rel = write_text(ctx, "ai/summary.md", result.content)

# read artifact/input file (path-traversal guarded)
input_text = read_text(ctx, str(raw_input["answer_text_path"]))
```

## 6. Configuration & Secrets (config.yaml)

`config.yaml` lives in the plugin directory (see `plugins/zhihu_digest/config.yaml`):

```yaml
defaults:
  timeout_seconds: 30
  mode: auto
  dry_run: false

secrets:
  cookie_env: ZHIHU_COOKIE
  cookie_file: ZHIHU_COOKIE_FILE
```

- **`defaults`**: passed through verbatim as `config["defaults"]`.
- **`secrets`**: each value names an environment variable; the loader resolves it (or `None` when unset) into `config["secrets"]`.
- Plugins read them in `__init__`: `self.config.get("defaults", {})` / `self.config.get("secrets", {})`.
- Without `config.yaml` the loader passes `config=None`.

See `plugins/openclaw/backend.py`: OpenClaw writes config into module-level `_DEFAULTS` / `_SECRETS` for handlers (plugins load once per process; `get_registry` is an `lru_cache` singleton, so this is safe).

## 7. Registry & Loading

### plugins.yaml

Enable plugins in `plugins/plugins.yaml`:

```yaml
plugins:
  zhihu_digest:
    enabled: true
  my_plugin:
    enabled: true
    path: examples/hello_world.py   # optional: file plugin or custom path
```

### Loading Flow (backend/app/runtime/plugin_loader.py)

1. Read enabled plugins from `plugins.yaml`
2. Import the module (directory plugins need `__init__.py`)
3. Discover `PLUGIN` (a `Plugin` subclass), instantiate with injected config
4. Call `plugin.register()` to register

### Error Handling

A failing plugin does not affect others; errors are recorded in the Registry (see the `errors` field of `GET /api/v1/plugins`).

## 8. Example Analysis

### dummy: simplest action

See `plugins/dummy/backend.py` (full code in Section 1).

**Features**: simplest structure; echoes context; no external dependencies.

### hello_world: file-plugin example

See `plugins/examples/hello_world.py`:

```python
from app.core.registry import ActionContext
from plugins.common.plugin import Plugin


def _hello(ctx: ActionContext, params: dict[str, Any]) -> Any:
    name = params.get("name", "World")
    return {"message": f"Hello, {name} from AutoFlow!"}


class HelloWorldPlugin(Plugin):
    """Example plugin: registers core.hello action"""

    name = "hello-world"
    version = "1.0.0"
    actions = {
        "core.hello": _hello,
    }
    checks = {}


PLUGIN = HelloWorldPlugin
```

**Features**: single-file plugin (no `__init__.py`); registers name and version.

### desktop_checkin: multiple actions/checks

See `plugins/desktop_checkin/backend.py`.

**Features**: 8 actions + 2 checks; desktop automation; uses `dry_run_enabled` / `is_truthy` / `safe_name`; dry-run support.

### zhihu_digest: external API calls

See `plugins/zhihu_digest/backend.py`.

**Features**: external API (zhihu, playwright); uses `read_text` / `write_text` / `utc_now_iso` / `dry_run_enabled`; data processing and storage; dry-run and error handling.

### openclaw: config injection

See `plugins/openclaw/backend.py`.

**Features**: constructor receives config.yaml defaults/secrets into module level; 3 actions + 2 checks; security: safe_mode on by default, `allowed_commands` whitelist.

## 9. Development Steps

1. Create `plugins/my_plugin/` with `__init__.py`
2. Define `class MyPlugin(Plugin)` in `backend.py` with `name` / `version` / `actions` / `checks` (module-level handlers)
3. Export `PLUGIN = MyPlugin` from `__init__.py`
4. Register in `plugins/plugins.yaml` (`enabled: true`)
5. Add `config.yaml` when configuration is needed (defaults + secrets)
6. Write tests and run `pytest plugins/my_plugin/tests` and `pytest backend/tests`
7. Validate with an example Flow (`docs/examples/*.flow.yaml`); use `vars: { dry_run: true }` first
