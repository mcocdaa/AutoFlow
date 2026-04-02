# @file /backend/app/core/database_manager.py
# @brief 数据库管理器 - SQLAlchemy 数据库连接和会话管理
# @create 2026-03-30

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.setting_manager import setting_manager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器

    职责：
    1. 管理 SQLAlchemy engine、Base 和 SessionLocal
    2. 提供数据库初始化函数
    3. 提供 FastAPI 依赖注入函数
    """

    def __init__(self):
        self._engine = None
        self._Base = None
        self._SessionLocal = None

    @property
    def engine(self):
        """获取 SQLAlchemy engine"""
        if self._engine is None:
            self._init_engine()
        return self._engine

    @property
    def Base(self):
        """获取 SQLAlchemy Base 声明基类"""
        if self._Base is None:
            self._Base = declarative_base()
        return self._Base

    @property
    def SessionLocal(self):
        """获取数据库会话工厂"""
        if self._SessionLocal is None:
            self._init_session_local()
        return self._SessionLocal

    def _init_engine(self):
        """初始化 SQLAlchemy engine"""
        database_url = (
            f"mysql+pymysql://{setting_manager.DB_USER}:{setting_manager.DB_PASSWORD}"
            f"@{setting_manager.DB_HOST}:{setting_manager.DB_PORT}/{setting_manager.DB_NAME}"
        )
        self._engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        logger.info(
            f"数据库 engine 已初始化: {setting_manager.DB_HOST}:{setting_manager.DB_PORT}"
        )

    def _init_session_local(self):
        """初始化 SessionLocal"""
        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def init_db(self) -> None:
        """初始化数据库，创建所有表"""
        try:
            self.Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表已创建")
        except Exception as e:
            logger.warning(f"数据库初始化失败（可能是因为数据库服务未启动）: {e}")

    def get_db(self) -> Generator[Session, None, None]:
        """FastAPI 依赖注入函数，获取数据库会话"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


database_manager = DatabaseManager()
