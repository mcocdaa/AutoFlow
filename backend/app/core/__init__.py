# @file /backend/app/core/__init__.py
# @brief Core 模块导出
# @create 2026-03-27
# @update 2026-08-22 移除 registry 模块级单例转发(单一入口为 runtime.get_registry)

from app.core.registry import ActionContext, CheckContext, Registry

__all__ = [
    "ActionContext",
    "CheckContext",
    "Registry",
]
