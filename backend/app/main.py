# @file /backend/app/main.py
# @brief FastAPI 应用入口，注册中间件和路由
# @create 2026-03-15 10:00:00
# @update 2026-03-27 集成新的插件管理器系统
# @update 2026-08-10 移除 env_secrets 文件密钥注入(allowlist 为空,属死代码)
# @update 2026-08-22 初始化收敛为模块级单次调用,静态文件开关依赖 setting_manager 归一化

import argparse
import logging

from app.api import register_routers
from app.core.setting_manager import setting_manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


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


# Module-level init is the single initialization path (uvicorn imports this
# module before serving; TestClient triggers it on import as well).
setting_manager.init(parse_args())

app = FastAPI(
    title=setting_manager.PROJECT_NAME,
    openapi_url=f"{setting_manager.API_V1_STR}/openapi.json",
    version=setting_manager.APP_VERSION,
)

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

if setting_manager.SERVE_STATIC_FILES:
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
