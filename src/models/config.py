from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Конфигурация приложения, загружаемая из .env файла."""
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
    db_default_password: Annotated[str, Field(min_length=1)]

    db_app_database: Annotated[str, Field(min_length=1)]
    db_app_username: Annotated[str, Field(min_length=1)]
    db_app_password: Annotated[str, Field(min_length=1)]

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
