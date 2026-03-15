# Proposal: AutoFlow Plugin v2 Upgrade

## Summary
将 `plugins/openclaw/` 插件从旧格式升级到 AutoFlow v2 插件规范，以适配上游 `main` 分支的重构。

## Background
上游 `main` 分支（commit `f3d6b8d`）对插件系统做了重大重构：
1. 入口文件从 `__init__.py` 改为 `backend.py`（loader 优先查找 `backend.py`）
2. registry import 路径从 `app.runtime.registry` 改为 `app.plugin.registry`
3. 新增 `plugin.yaml`（插件元信息）和 `config.yaml`（配置声明）

## Problem
当前 `openclaw` 分支的 `plugins/openclaw/__init__.py` 使用旧 import 路径：
```python
from app.runtime.registry import ActionContext, CheckContext  # ❌ 旧路径
```
在 v2 版本的 AutoFlow 中加载时会报 `ModuleNotFoundError`，导致插件无法注册。

## Proposed Changes
1. **新增 `plugins/openclaw/backend.py`**：将现有 `__init__.py` 内容迁移，修正 import 路径为 `app.plugin.registry`
2. **新增 `plugins/openclaw/plugin.yaml`**：插件元信息声明
3. **新增 `plugins/openclaw/config.yaml`**：配置和 secrets 声明
4. **保留 `plugins/openclaw/__init__.py`**：兼容旧版 loader（内容可为空或保留原内容）
5. **合并上游 main 更新**：将 `FETCH_HEAD` merge 到 `openclaw` 分支

## Scope
- 文件：`plugins/openclaw/backend.py`（新增）
- 文件：`plugins/openclaw/plugin.yaml`（新增）
- 文件：`plugins/openclaw/config.yaml`（新增）
- 文件：`plugins/openclaw/__init__.py`（保留，兼容）
- Git：merge `origin/main` → `openclaw`

## Rollback Plan
若升级失败，回退到 `__init__.py` 方式（loader 仍兼容），或 `git revert` 本次提交。

## Success Criteria
- AutoFlow 启动后 `/api/v1/plugins` 返回 `openclaw` 插件
- 3 个 actions + 2 个 checks 全部注册成功
- 现有测试通过
