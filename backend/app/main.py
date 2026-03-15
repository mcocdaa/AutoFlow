# @file /backend/app/main.py
# @brief FastAPI 应用入口，注册中间件和路由
# @create 2026-03-15 10:00:00

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import register_routers
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)

if settings.SERVE_STATIC_FILES:
    from pathlib import Path
    static_dir = settings.STATIC_FILES_DIR
    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        print(f"Warning: Static files directory {static_dir} not found. Skipping static file serving.")
else:
    @app.get("/")
    async def root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} API", "version": settings.APP_VERSION, "docs": "/docs"}
