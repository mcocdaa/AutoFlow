# @file /backend/app/main.py
# @brief FastAPI 应用入口，注册中间件和路由
# @create 2026-03-15 10:00:00
# @update 2026-03-27 集成新的插件管理器系统

import argparse
import logging
from contextlib import asynccontextmanager

from app.api import register_routers
from app.core.env_secrets import apply_file_env
from app.core.setting_manager import setting_manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

_services_initialized = False


def parse_args():
    """解析命令行参数"""
    import sys

    # pytest (TestClient) early‑return: skip argument parsing entirely
    if "pytest" in sys.modules:
        return argparse.Namespace()

    parser = argparse.ArgumentParser(description="AutoFlow Backend")
    setting_manager.register_arguments(parser)
    # parse_known_args() tolerates unknown args (e.g. uvicorn's "app.main:app")
    return parser.parse_known_args()[0]


def init_services():
    """初始化所有服务"""
    global _services_initialized
    if _services_initialized:
        return
    apply_file_env()
    args = parse_args()
    setting_manager.init(args)
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

# Always call init_services() at module level (idempotent gate)
init_services()

app.add_middleware(
    CORSMiddleware,
    allow_origins=setting_manager.CORS_ORIGINS or ["*"],
    allow_credentials=(False if setting_manager.CORS_ORIGINS == ["*"] else True),
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
            f"Static files directory {static_dir} not found. "
            "Skipping static file serving."
        )
else:

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {setting_manager.PROJECT_NAME} API",
            "version": setting_manager.APP_VERSION,
            "docs": "/docs",
        }
