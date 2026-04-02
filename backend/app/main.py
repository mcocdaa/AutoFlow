# @file /backend/app/main.py
# @brief FastAPI 应用入口，注册中间件和路由
# @create 2026-03-15 10:00:00
# @update 2026-03-27 集成新的插件管理器系统
# @update 2026-03-30 添加数据库初始化

import argparse
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import register_routers
from app.core.database_manager import database_manager
from app.core.plugin_manager import plugin_manager
from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)

_services_initialized = False


def init_services():
    """初始化所有服务"""
    global _services_initialized
    if _services_initialized:
        return
    # 使用空的 Namespace，配置通过环境变量和 .env 文件处理
    args = argparse.Namespace()
    setting_manager.init(args)
    plugin_manager.init(args)
    # 在测试环境下不初始化数据库
    import sys

    if "pytest" not in sys.modules:
        try:
            database_manager.init_db()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.warning(f"数据库初始化失败: {e}")
    _services_initialized = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    init_services()
    yield


app = FastAPI(
    title=setting_manager.PROJECT_NAME,
    openapi_url=f"{setting_manager.API_STR}/openapi.json",
    version=setting_manager.APP_VERSION,
    lifespan=lifespan,
)

# 初始化服务（在所有环境下都初始化 setting_manager 和 plugin_manager，但在测试环境下不初始化数据库）
import sys

init_services()

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
