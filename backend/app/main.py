# @file /backend/app/main.py
# @brief FastAPI 应用入口，注册中间件和路由
# @create 2026-03-15 10:00:00
# @update 2026-03-27 集成新的插件管理器系统

import argparse
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import register_routers
from app.core.plugin_manager import plugin_manager
from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)

_services_initialized = False


def parse_args():
    """解析命令行参数"""
    import sys

    # 检查是否是 pytest 或其他不是 uvicorn 的场景
    if "pytest" in sys.modules or "uvicorn" not in sys.argv[0]:
        return argparse.Namespace()
    # 正常 uvicorn 启动，尝试解析参数
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1].startswith("-")):
        return argparse.Namespace()
    parser = argparse.ArgumentParser(description="AutoFlow Backend")
    setting_manager.register_arguments(parser)
    plugin_manager.register_arguments(parser)
    return parser.parse_args()


def init_services():
    """初始化所有服务"""
    global _services_initialized
    if _services_initialized:
        return
    args = parse_args()
    setting_manager.init(args)
    plugin_manager.init(args)
    _services_initialized = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    init_services()
    yield


app = FastAPI(
    title=setting_manager.PROJECT_NAME,
    openapi_url=f"{setting_manager.API_V1_STR}/openapi.json",
    version=setting_manager.APP_VERSION,
    lifespan=lifespan,
)

# 确保在导入模块时也初始化（用于 TestClient 场景）
try:
    import pytest

    init_services()
except ImportError:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

register_routers(app)

if (
    setting_manager.SERVE_STATIC_FILES == "True"
    or setting_manager.SERVE_STATIC_FILES is True
):
    from pathlib import Path

    static_dir = setting_manager.STATIC_FILES_DIR
    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        logger.warning(
            f"Static files directory {static_dir} not found. Skipping static file serving."
        )
else:

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {setting_manager.PROJECT_NAME} API",
            "version": setting_manager.APP_VERSION,
            "docs": "/docs",
        }
