# @file /backend/app/core/setting_manager.py
# @brief 配置管理器 - 负责参数解析和全局配置
# @create 2026-03-27

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from app.core.hook_manager import hook_manager

ROOT_DIR = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


class SettingManager:
    """配置管理器

    职责：
    1. 管理全局配置（动态+静态）
    2. 注册核心参数到 argparse
    3. 通过 get() 或属性访问配置

    使用流程：
    1. __init__() 初始化配置存储，加载 .env 文件
    2. register_arguments(parser) 注册参数
    3. init(args) 解析参数
    """

    @hook_manager.wrap_hooks(
        "setting_manager_construct_before", "setting_manager_construct_after"
    )
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self._log_config_called = False
        self._load_env()

    def _load_env(self):
        """从 .env 文件加载环境变量"""
        env_path = ROOT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        for key, value in os.environ.items():
            self.config[key] = value

        self.config.setdefault("PROJECT_NAME", "AutoFlow")
        self.config.setdefault("APP_VERSION", "0.1.0")
        self.config.setdefault("API_VERSION", "v1")
        self.config.setdefault("BACKEND_INTERNAL_PORT", 3000)
        self.config.setdefault("BACKEND_EXTERNAL_PORT", 3001)
        self.config.setdefault("FRONTEND_INTERNAL_PORT", 8000)
        self.config.setdefault("FRONTEND_EXTERNAL_PORT", 8001)
        self.config.setdefault("BACKEND_PORT", 8000)
        self.config.setdefault("FRONTEND_PORT", 3001)
        self.config.setdefault("DB_EXTERNAL_PORT", 3306)
        self.config.setdefault("REDIS_EXTERNAL_PORT", 6379)
        self.config.setdefault("LOG_LEVEL", "INFO")
        self.config.setdefault("DB_USER", "autoflow")
        self.config.setdefault("DB_NAME", "autoflow_db")
        self.config.setdefault("REDIS_DB", 0)
        self.config.setdefault("SERVE_STATIC_FILES", "False")
        self.config.setdefault("STATIC_FILES_DIR", "/app/static")
        self.config.setdefault("DB_HOST", "mysql")
        self.config.setdefault("DB_PORT", 3306)
        self.config.setdefault("REDIS_HOST", "redis")
        self.config.setdefault("REDIS_PORT", 6379)
        self.config.setdefault("DB_PASSWORD", "")
        self.config.setdefault("SECRET_KEY", "")

        self.config["ROOT_DIR"] = str(ROOT_DIR)
        self.config["BACKEND_DIR"] = str(BACKEND_DIR)
        self.config["PLUGINS_DIR"] = str(ROOT_DIR / "plugins")
        self.config["API_V1_STR"] = f"/api/{self.config['API_VERSION']}"
        self.config["REDIS_URL"] = (
            f"redis://{self.config['REDIS_HOST']}:{self.config['REDIS_PORT']}/{self.config['REDIS_DB']}"
        )
        self.config["PORT"] = int(
            os.getenv("PORT", self.config["BACKEND_INTERNAL_PORT"])
        )

    @hook_manager.wrap_hooks(after="setting_manager_register_arguments")
    def register_arguments(self, parser: argparse.ArgumentParser):
        """注册核心参数

        Args:
            parser: argparse.ArgumentParser 实例
        """
        group = parser.add_argument_group("Core", "Core Parameters")

        group.add_argument(
            "--host",
            type=str,
            default=os.getenv("HOST", "0.0.0.0"),
            help="绑定地址 (默认: 0.0.0.0)",
        )

        group.add_argument(
            "--port",
            type=int,
            default=int(os.getenv("PORT", "3001")),
            help="绑定端口 (默认: 3001)",
        )

        group.add_argument(
            "--log-level",
            type=str,
            default=os.getenv("LOG_LEVEL", "INFO"),
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"],
            help="日志级别 (默认: INFO)",
        )

        group.add_argument(
            "--cors-origins",
            type=str,
            default=os.getenv("CORS_ORIGINS", "*"),
            help="CORS 允许的源，逗号分隔 (默认: *)",
        )

    @hook_manager.wrap_hooks(
        "setting_manager_init_before", "setting_manager_init_after"
    )
    def init(self, args: argparse.Namespace):
        """解析并设置配置

        Args:
            args: 解析后的 argparse.Namespace
        """
        self.config["HOST"] = getattr(args, "host", self.config.get("HOST", "0.0.0.0"))
        self.config["PORT"] = getattr(args, "port", self.config.get("PORT", 3001))
        self.config["LOG_LEVEL"] = getattr(
            args, "log_level", self.config.get("LOG_LEVEL", "INFO")
        )

        cors_origins_val = getattr(
            args, "cors_origins", self.config.get("CORS_ORIGINS", "*")
        )
        if isinstance(cors_origins_val, list):
            self.config["CORS_ORIGINS"] = cors_origins_val
        else:
            self.config["CORS_ORIGINS"] = [
                o.strip() for o in str(cors_origins_val).split(",")
            ]

        logging.basicConfig(
            level=getattr(logging, self.config["LOG_LEVEL"]),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self._log_config()

    def _log_config(self):
        """记录配置"""
        if self._log_config_called:
            return
        self._log_config_called = True
        logger = logging.getLogger(__name__)
        logger.info("=" * 50)
        logger.info("应用配置")
        logger.info("=" * 50)
        important_keys = [
            "PROJECT_NAME",
            "APP_VERSION",
            "ROOT_DIR",
            "BACKEND_DIR",
            "PLUGINS_DIR",
            "HOST",
            "PORT",
            "LOG_LEVEL",
            "API_VERSION",
        ]
        for key in important_keys:
            if key in self.config:
                logger.info(f"{key}: {self.config[key]}")
        logger.info("=" * 50)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（key 自动转大写）"""
        return self.config.get(key.upper(), default)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.config.get(name.upper())

    def set(self, key: str, value: Any):
        """设置配置项（key 自动转大写）"""
        self.config[key.upper()] = value


setting_manager = SettingManager()
