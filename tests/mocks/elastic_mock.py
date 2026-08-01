from datetime import datetime, timezone

from src.elastic import (
    ElasticBlogpostsServiceBase,
    ElasticDocumentsServiceBase,
    ElasticMigrationsBase,
    ElasticServiceBase,
)
from src.exceptions import NotFoundException, UpdateConflict
from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostUpdate


class ElasticDocumentsServiceMock(ElasticDocumentsServiceBase):
    """Заглушка документных операций elastic-сервиса с реестром вызовов."""

    def __init__(self) -> None:
        self._search_results: dict[str, list[int]] = {}
        self.search_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.raise_on_search: Exception | None = None
        self.raise_on_delete: Exception | None = None

    def set_search_result(self, query: str, ids: list[int]) -> None:
        """Задать результат поиска для конкретного запроса."""
        self._search_results[query] = ids

    async def search(self, query: str) -> list[int]:
        if self.raise_on_search is not None:
            raise self.raise_on_search
        self.search_calls.append({"query": query})
        return self._search_results.get(query, [])

    async def delete(self, doc_id: int) -> None:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.delete_calls.append({"doc_id": doc_id})


class ElasticBlogpostsServiceMock(ElasticBlogpostsServiceBase):
    """Заглушка операций с блогпостами elastic-сервиса."""

    def __init__(self) -> None:
        self.index_blogposts_calls: list[dict] = []
        self.create_calls: list[dict] = []
        self.get_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.delete_calls: list[dict] = []

        self._blogposts: dict[str, Blogpost] = {}
        self._id_counter: int = 0

        self.raise_on_create: Exception | None = None
        self.raise_on_get: Exception | None = None
        self.raise_on_update: Exception | None = None
        self.raise_on_delete: Exception | None = None

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"mock-{self._id_counter}"

    async def index_blogposts(self, blogposts: list) -> None:
        self.index_blogposts_calls.append({"blogposts": blogposts})

    async def create(self, data: BlogpostCreate) -> Blogpost:
        if self.raise_on_create is not None:
            raise self.raise_on_create
        self.create_calls.append({"data": data})
        body = data.model_dump(exclude_none=True)
        doc_id = body.pop("id", None)
        if doc_id is not None and doc_id in self._blogposts:
            raise UpdateConflict(
                f"Блогпост с id '{doc_id}' уже существует."
            )
        bp = Blogpost(
            id=doc_id if doc_id is not None else self._next_id(),
            title=body["title"],
            text=body["text"],
            tags=body.get("tags", []),
            updated_at=body.get(
                "updated_at",
                datetime.now(timezone.utc),
            ),
        )
        self._blogposts[bp.id] = bp
        return bp

    async def get(self, blogpost_id: str) -> Blogpost:
        if self.raise_on_get is not None:
            raise self.raise_on_get
        self.get_calls.append({"blogpost_id": blogpost_id})
        if blogpost_id not in self._blogposts:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")
        return self._blogposts[blogpost_id]

    async def update(self, blogpost_id: str, data: BlogpostUpdate) -> Blogpost:
        if self.raise_on_update is not None:
            raise self.raise_on_update
        self.update_calls.append({"blogpost_id": blogpost_id, "data": data})
        if blogpost_id not in self._blogposts:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")
        bp = self._blogposts[blogpost_id]
        update_data = data.model_dump(exclude_none=True)
        updated = bp.model_copy(update=update_data)
        self._blogposts[blogpost_id] = updated
        return updated

    async def delete(self, blogpost_id: str) -> None:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.delete_calls.append({"blogpost_id": blogpost_id})
        self._blogposts.pop(blogpost_id, None)


class ElasticMigrationsMock(ElasticMigrationsBase):
    """Заглушка миграций elastic-сервиса."""

    async def upgrade(self, current: str, to: str) -> None:
        pass

    async def downgrade(self, current: str, to: str) -> None:
        pass

    async def delete_indices(self) -> None:
        pass


class ElasticServiceMock(ElasticServiceBase):
    """Заглушка фасада elastic-сервиса с реестром вызовов для тестов."""

    def __init__(self) -> None:
        self._documents = ElasticDocumentsServiceMock()
        self._blogposts = ElasticBlogpostsServiceMock()
        self._migrations = ElasticMigrationsMock()

    @property
    def documents(self) -> ElasticDocumentsServiceMock:
        return self._documents

    @property
    def blogposts(self) -> ElasticBlogpostsServiceMock:
        return self._blogposts

    @property
    def migrations(self) -> ElasticMigrationsMock:
        return self._migrations

    async def close(self) -> None:
        pass
