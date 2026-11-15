"""Backend configuration loaded from the environment."""

import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app._paths import REPO_ROOT

_DEFAULT_SQLITE_PATH = os.path.join(REPO_ROOT, "myhr.db")
_DEFAULT_DATABASE_URL = f"sqlite:///{_DEFAULT_SQLITE_PATH}"


class Settings(BaseSettings):
    """Application settings.

    The database engine is config-switchable through ``MYHR_DATABASE_URL``.
    When unset it defaults to the existing desktop SQLite database so local
    development matches the desktop app. Set a ``postgresql+psycopg://`` URL
    to point at Postgres later.
    """

    model_config = SettingsConfigDict(env_prefix="MYHR_", env_file=".env", extra="ignore")

    app_name: str = "MyHR API"
    database_url: str = _DEFAULT_DATABASE_URL

    @field_validator("database_url")
    @classmethod
    def select_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


def get_settings() -> Settings:
    return Settings()
