from pathlib import Path

from app.core.env_secrets import apply_file_env
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(str(_ENV_PATH), override=False)
apply_file_env()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoFlow"
    API_V1_STR: str = "/api/v1"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "autoflow"
    DB_PASSWORD: str = "dev_password"
    DB_NAME: str = "autoflow_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    SECRET_KEY: str = "dev_secret_key"

    model_config = SettingsConfigDict(env_file=str(_ENV_PATH), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
