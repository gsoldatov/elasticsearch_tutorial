from abc import ABC, abstractmethod


class ElasticServiceBase(ABC):
    """Абстрактный класс для сервиса, взаимодействующего с ES."""
    @abstractmethod
    async def search(self, query: str) -> list[int]:
        """Поиск документов по текстовому запросу. Возвращает список id."""

    @abstractmethod
    async def delete(self, doc_id: int) -> None:
        """Удаление документа из поискового индекса."""

    async def close(self) -> None:
        """Освобождение ресурсов (переопределяется в конкретных реализациях)."""
