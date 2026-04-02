# @file /app/api/__init__.py
# @brief API 路由总入口 - 支持版本控制
# @create 2026-03-10

import importlib

from fastapi import FastAPI

from app.core.setting_manager import setting_manager


def register_routers(app: FastAPI):
    """
    自动注册 API 路由：
    1. 注册 v1 和 v2 版本的路由
    2. 每个版本的路由使用自己的前缀
    """
    for api_version in ["v1", "v2"]:
        version_package_name = f"{__name__}.{api_version}"
        try:
            version_package = importlib.import_module(version_package_name)
            if hasattr(version_package, "router"):
                app.include_router(version_package.router, tags=[api_version.upper()])
                print(f"[Route] 已注册 API 版本: {api_version}")
        except ModuleNotFoundError:
            continue
