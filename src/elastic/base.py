from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Awaitable

from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostSearchResult, BlogpostUpdate
from src.models.document import Document

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

    async def index_documents(self, documents: list[Document]) -> None:
        """Массовая индексация документов."""


class ElasticBlogpostsServiceBase(ABC):
    """Абстрактный класс для операций с блогпостами в ES."""

    @abstractmethod
    async def index_blogposts(self, blogposts: list[Blogpost]) -> None:
        """Массовая индексация блогпостов."""

    @abstractmethod
    def create(self, data: BlogpostCreate) -> Awaitable[Blogpost]:
        """Создание блогпоста. Возвращает созданный объект."""

    @abstractmethod
    def get(self, blogpost_id: str) -> Awaitable[Blogpost]:
        """Получение блогпоста по id."""

    @abstractmethod
    def update(self, blogpost_id: str, data: BlogpostUpdate) -> Awaitable[Blogpost]:
        """Частичное обновление блогпоста с optimistic lock."""

    @abstractmethod
    async def delete(self, blogpost_id: str) -> None:
        """Удаление блогпоста."""

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        min_time: datetime | None = None,
        max_time: datetime | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Awaitable[BlogpostSearchResult]:
        """Полнотекстовый поиск блогпостов с фильтрами и пагинацией."""


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
