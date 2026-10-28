from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KeyGate"
    app_env: str = "development"
    debug: bool = False
    database_url: str
    database_connect_timeout: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
