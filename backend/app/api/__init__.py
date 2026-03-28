# @file /app/api/__init__.py
# @brief API 路由总入口 - 支持版本控制
# @create 2026-03-10

import importlib

from fastapi import FastAPI

from app.core.setting_manager import setting_manager


def register_routers(app: FastAPI):
    """
    自动注册指定版本的 API 路由：
    1. 根据 settings.API_VERSION 获取版本号 (如 v1)
    2. 动态导入版本包 (如 app.api.v1)
    3. 查找该包下的全局 `router` 对象并挂载
    """
    api_version = setting_manager.API_VERSION

    version_package_name = f"{__name__}.{api_version}"

    try:
        version_package = importlib.import_module(version_package_name)
    except ModuleNotFoundError:
        raise RuntimeError(f"API 版本模块不存在: {version_package_name}")

    if hasattr(version_package, "router"):
        app.include_router(
            version_package.router, prefix=f"/api", tags=[api_version.upper()]
        )
        print(f"[Route] 已注册 API 版本: {api_version}, 前缀: /api")
    else:
        raise AttributeError(f"模块 {version_package_name} 中未找到 'router' 对象")
