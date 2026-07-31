from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.models.blogpost import Blogpost

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


class ElasticBlogpostsServiceBase(ABC):
    """Абстрактный класс для операций с блогпостами в ES."""

    @abstractmethod
    async def index_blogposts(self, blogposts: list[Blogpost]) -> None:
        """Массовая индексация блогпостов."""

    @abstractmethod
    async def create(self, data: dict) -> Blogpost:
        """Создание блогпоста. Возвращает созданный объект."""

    @abstractmethod
    async def get(self, blogpost_id: str) -> Blogpost:
        """Получение блогпоста по id."""

    @abstractmethod
    async def update(self, blogpost_id: str, data: dict) -> Blogpost:
        """Частичное обновление блогпоста с optimistic lock."""

    @abstractmethod
    async def delete(self, blogpost_id: str) -> None:
        """Удаление блогпоста."""


class ElasticServiceBase(ABC):
    """Абстрактный класс для фасада ES-сервиса."""

    @property
    @abstractmethod
    def documents(self) -> ElasticDocumentsServiceBase:
        """Документные операции."""

    @property
    @abstractmethod
    def blogposts(self) -> ElasticBlogpostsServiceBase:
        """Операции с блогпостами."""

    @property
    @abstractmethod
    def migrations(self) -> ElasticMigrationsBase:
        """Миграции ES."""

    @abstractmethod
    async def close(self) -> None:
        """Освобождение ресурсов."""
