from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import TYPE_CHECKING, Awaitable

from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostSearchResult, BlogpostUpdate
from src.models.document import Document
from src.models.sales import Sale, SalesByMonthRegionItem, TopProductItem, UnitsSoldGroupItem

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

    @abstractmethod
    async def search_tags(self, q: str) -> list[str]:
        """Нечёткий префиксный поиск по тегам. Возвращает уникальные теги."""


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
    def sales(self) -> ElasticSalesServiceBase:
        """Операции с продажами."""

    @property
    @abstractmethod
    def migrations(self) -> ElasticMigrationsBase:
        """Миграции ES."""

    @abstractmethod
    async def close(self) -> None:
        """Освобождение ресурсов."""


class ElasticSalesServiceBase(ABC):
    """Абстрактный класс для операций с продажами в ES."""

    @abstractmethod
    async def index_sales(self, sales: list[Sale]) -> None:
        """Массовая индексация продаж."""

    @abstractmethod
    def by_month_and_region(
        self,
        *,
        min_date: date | None = None,
        max_date: date | None = None,
        regions: list[str] | None = None,
        products: list[str] | None = None,
    ) -> Awaitable[list[SalesByMonthRegionItem]]:
        """Агрегация выручки по месяцам и регионам с фильтрами."""

    @abstractmethod
    def top_products(
        self,
        *,
        n: int = 10,
        min_date: date | None = None,
        max_date: date | None = None,
        regions: list[str] | None = None,
    ) -> Awaitable[list[TopProductItem]]:
        """Топ-n продуктов по выручке для каждого региона."""

    @abstractmethod
    def units_sold_groups(
        self,
        *,
        min_date: date | None = None,
        max_date: date | None = None,
        regions: list[str] | None = None,
        products: list[str] | None = None,
    ) -> Awaitable[list[UnitsSoldGroupItem]]:
        """Группировка выручки по интервалам units_sold (1-10, 11-20, ...)."""
