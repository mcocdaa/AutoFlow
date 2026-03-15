# @file /backend/app/core/config.py
# @brief 应用配置管理，区分外部可配置项与内部固定项
# @create 2026-03-15 10:00:00

from pathlib import Path

from app.core.env_secrets import apply_file_env
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(str(_ENV_PATH), override=False)
apply_file_env()


class Settings(BaseSettings):
    # ==================== 外部可配置项 ====================
    # 用户可在 .env 中修改这些配置

    # 项目配置
    PROJECT_NAME: str = "AutoFlow"
    APP_VERSION: str = "0.1.0"
    API_VERSION: str = "v1"

    # 外部端口（Docker 映射到宿主机的端口）
    BACKEND_PORT: int = 8000
    DB_PORT_OUTER: int = 3306
    REDIS_PORT_OUTER: int = 6379

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # 数据库配置（外部可修改）
    DB_USER: str = "autoflow"
    DB_NAME: str = "autoflow_db"

    # Redis 配置（外部可修改）
    REDIS_DB: int = 0

    # 静态文件服务配置
    SERVE_STATIC_FILES: bool = False
    STATIC_FILES_DIR: str = "/app/static"

    # 插件配置
    AUTOFLOW_PLUGIN_DIRS: str = ""

    # ==================== 内部固定项 ====================
    # Docker 网络内部通信配置，用户通常不需要修改

    # 数据库内部配置（Docker 网络中固定）
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306

    # Redis 内部配置（Docker 网络中固定）
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # 私有配置（从 secrets 文件读取）
    DB_PASSWORD: str = ""
    SECRET_KEY: str = ""

    # 派生配置
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def API_V1_STR(self) -> str:
        return f"/api/{self.API_VERSION}"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
