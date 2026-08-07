from typing import Annotated, Any

from pydantic import BeforeValidator, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_keep_alive(v: Any) -> int | str:
    """Превращает числовые строки ('-1') в int, остальное оставляет как str."""
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return v
    return v


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

    es_host: Annotated[str, Field(min_length=1)]
    es_port: Annotated[int, Field(gt=0, lt=65536)]
    es_superuser_password: Annotated[str, Field(min_length=1)]
    es_documents_index_name: Annotated[str, Field(min_length=1)]
    es_blogposts_index_name: Annotated[str, Field(min_length=1)]
    es_blogposts_text_chunks_index_name: Annotated[str, Field(min_length=1)]
    es_sales_index_name: Annotated[str, Field(min_length=1)]

    ollama_host: Annotated[str, Field(min_length=1)]
    ollama_port: Annotated[int, Field(gt=0, lt=65536)]
    ollama_model: Annotated[str, Field(min_length=1)]
    ollama_timeout: Annotated[int, Field(gt=0)]
    ollama_batch_size: Annotated[int, Field(gt=0)]
    ollama_keep_alive: Annotated[int | str, BeforeValidator(_parse_keep_alive)]
    ollama_tokenizer: Annotated[str, Field(min_length=1)]

    @field_validator("ollama_keep_alive", mode="after")
    @classmethod
    def _validate_keep_alive_not_empty(cls, v: int | str) -> int | str:
        if isinstance(v, str) and v == "":
            raise ValueError("ollama_keep_alive не может быть пустой строкой")
        return v

    @property
    def db_app_url(self) -> str:
        return (
            f"postgresql://"
            f"{self.db_app_username}:{self.db_app_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_app_database}"
        )

    @property
    def db_app_sa_url(self) -> str:
        return self.db_app_url.replace("postgresql://", "postgresql+psycopg://")

    @property
    def db_default_url(self) -> str:
        return (
            f"postgresql://"
            f"{self.db_default_username}:{self.db_default_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_default_database}"
        )

    @property
    def es_url(self) -> str:
        return f"http://{self.es_host}:{self.es_port}"

    @property
    def es_indices(self) -> dict[str, str]:
        """Возвращает словарь {имя_поля: имя_индекса} для всех ES-индексов."""
        return {
            attr: getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("es_") and attr.endswith("_index_name")
        }

    @property
    def ollama_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"
