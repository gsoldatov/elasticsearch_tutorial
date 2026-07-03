from src.elastic import ElasticServiceBase


class ElasticServiceMock(ElasticServiceBase):
    """Заглушка elastic-сервиса с реестром вызовов для тестов."""

    def __init__(self) -> None:
        self._search_results: dict[str, list[int]] = {}
        self.search_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def set_search_result(self, query: str, ids: list[int]) -> None:
        """Задать результат поиска для конкретного запроса."""
        self._search_results[query] = ids

    async def search(self, query: str) -> list[int]:
        self.search_calls.append({"query": query})
        return self._search_results.get(query, [])

    async def delete(self, doc_id: int) -> None:
        self.delete_calls.append({"doc_id": doc_id})
