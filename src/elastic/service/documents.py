from typing import TYPE_CHECKING

from elasticsearch import NotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticDocumentsServiceBase

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticDocumentsService(ElasticDocumentsServiceBase):
    """Документные операции ES: индекс, поиск, удаление."""

    INDEX_SETTINGS = {
        "settings": {"number_of_replicas": 0},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "text": {"type": "text", "analyzer": "russian"},
            },
        },
    }

    def __init__(self, _es: "ElasticService") -> None:
        self._es = _es

    @property
    def client(self):
        return self._es.client

    async def search(self, query: str) -> list[int]:
        """Поиск документов по тексту. Возвращает список id."""
        response = await self.client.search(
            index=self._es._config.es_documents_index_name,
            body={
                "query": {
                    "match_phrase": {
                        "text": query,
                    },
                },
            },
        )
        return [int(hit["_id"]) for hit in response["hits"]["hits"]]

    async def delete(self, doc_id: int) -> None:
        """Удаление документа из поискового индекса."""
        try:
            await self.client.delete(
                index=self._es._config.es_documents_index_name,
                id=str(doc_id),
                refresh=self._es._refresh,
            )
        except NotFoundError as e:
            if e.body and isinstance(e.body, dict) and e.body.get("result") != "not_found":
                raise

    async def create_index(self) -> None:
        """Создаёт индекс с маппингом. Идемпотентно."""
        await self.client.options(ignore_status=400).indices.create(
            index=self._es._config.es_documents_index_name,
            **self.INDEX_SETTINGS,
        )

    async def delete_index(self) -> None:
        """Удаляет индекс."""
        await self.client.options(ignore_status=[404]).indices.delete(
            index=self._es._config.es_documents_index_name,
        )

    async def index_documents(self, documents: list[dict]) -> None:
        """Массовая индексация документов.

        Каждый документ — словарь с ключами 'id' и 'text'.
        """
        actions = [
            {
                "_index": self._es._config.es_documents_index_name,
                "_id": str(doc["id"]),
                "_source": {
                    "id": doc["id"],
                    "text": doc["text"],
                },
            }
            for doc in documents
        ]
        await async_bulk(self.client, actions, refresh=self._es._refresh)
