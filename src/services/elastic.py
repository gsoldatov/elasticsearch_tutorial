from src.types.elastic import ElasticServiceBase


class ElasticService(ElasticServiceBase):
    """Сервисный класс для взаимодействия с ES."""
    async def search(self, query: str) -> list[int]:
        return []

    async def delete(self, doc_id: int) -> None:
        pass
