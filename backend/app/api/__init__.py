# @file /app/api/__init__.py
# @brief API 路由总入口 - 支持版本控制
# @create 2026-03-10

import importlib
from fastapi import FastAPI
from app.core.config import settings


def register_routers(app: FastAPI):
    """
    自动注册指定版本的 API 路由：
    1. 根据 settings.API_V1_STR 提取版本号 (如 v1)
    2. 动态导入版本包 (如 app.api.v1)
    3. 查找该包下的全局 `router` 对象并挂载
    """
    # 1. 从 API_V1_STR 中提取版本号 (例如: "/api/v1" -> "v1")
    api_version = settings.API_V1_STR.strip("/").split("/")[-1]
    
    # 2. 构建完整的包路径字符串 (例如: "app.api.v1")
    version_package_name = f"{__name__}.{api_version}"

    try:
        # 3. 动态导入版本模块
        version_package = importlib.import_module(version_package_name)
    except ModuleNotFoundError:
        raise RuntimeError(f"API 版本模块不存在: {version_package_name}")

    # 4. 检查并挂载路由
    if hasattr(version_package, "router"):
        app.include_router(
            version_package.router,
            prefix=f"/api",
            tags=[api_version.upper()] # 标签显示为 "V1"，更醒目
        )
        print(f"[Route] 已注册 API 版本: {api_version}, 前缀: /api")
    else:
        raise AttributeError(f"模块 {version_package_name} 中未找到 'router' 对象")
