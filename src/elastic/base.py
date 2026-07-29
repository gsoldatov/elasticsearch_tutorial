from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.elastic.service.migrations.base import ElasticMigrationsBase


class ElasticDocumentsServiceBase(ABC):
    """Абстрактный класс для документных операций с ES."""

    @abstractmethod
    async def search(self, query: str) -> list[int]:
        """Поиск документов по текстовому запросу. Возвращает список id."""

    @abstractmethod
    async def delete(self, doc_id: int) -> None:
        """Удаление документа из поискового индекса."""

    async def index_documents(self, documents: list[dict]) -> None:
        """Массовая индексация документов."""


class ElasticServiceBase(ABC):
    """Абстрактный класс для фасада ES-сервиса."""

    @property
    @abstractmethod
    def documents(self) -> ElasticDocumentsServiceBase:
        """Документные операции."""

    @property
    @abstractmethod
    def migrations(self) -> ElasticMigrationsBase:
        """Миграции ES."""

    @abstractmethod
    async def close(self) -> None:
        """Освобождение ресурсов."""
