# @file backend/app/api/v1/__init__.py
# @brief API v1 模块导出
# @create 2026-03-10

from pathlib import Path

from app.api.v1 import flows
from app.core.router_loader import include_routers_from_directory
from fastapi import APIRouter

# 1. 创建父路由
router = APIRouter()

# 2. 注册服务端 Flow CRUD 路由 (/api/v1/flows, flows.router 已声明 prefix="/flows", tags=["flows"])
router.include_router(flows.router, prefix="/v1", tags=["flows"])

# 3. 调用工具函数，自动加载当前目录下的其余子路由
include_routers_from_directory(
    parent_router=router,
    package_name=__package__,
    directory_path=Path(__file__).parent,
    auto_tag=False,
    auto_prefix=False,
    skip_modules=["flows"],
)
