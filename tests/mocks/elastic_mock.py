from src.elastic import ElasticDocumentsServiceBase, ElasticMigrationsBase, ElasticServiceBase


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
        self._migrations = ElasticMigrationsMock()

    @property
    def documents(self) -> ElasticDocumentsServiceMock:
        return self._documents

    @property
    def migrations(self) -> ElasticMigrationsMock:
        return self._migrations

    async def close(self) -> None:
        pass
