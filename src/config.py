from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_host: Annotated[str, Field(min_length=1)]
    backend_port: Annotated[int, Field(gt=0, lt=65536)]

    db_host: Annotated[str, Field(min_length=1)]
    db_port: Annotated[int, Field(gt=0, lt=65536)]

    db_default_database: Annotated[str, Field(min_length=1)]
    db_default_username: Annotated[str, Field(min_length=1)]
    db_default_password: str

    db_app_database: Annotated[str, Field(min_length=1)]
    db_app_username: Annotated[str, Field(min_length=1)]
    db_app_password: str

    @property
    def db_app_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.db_app_username}:{self.db_app_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_app_database}"
        )

    @property
    def db_default_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.db_default_username}:{self.db_default_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_default_database}"
        )


def get_config(env_path: str | Path | None = None) -> Config:
    if env_path is None:
        resolved = PROJECT_ROOT / ".env"
    else:
        resolved = Path(env_path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved

    if not resolved.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {resolved}")

    return Config(_env_file=resolved)
