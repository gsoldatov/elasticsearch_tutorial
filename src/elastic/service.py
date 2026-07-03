from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from elastic_transport._node._http_httpx import HttpxAsyncHttpNode

from src.config import Config
from src.elastic.base import ElasticServiceBase


class ElasticService(ElasticServiceBase):
    """Реализация ElasticServiceBase через AsyncElasticsearch."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: AsyncElasticsearch | None = None

    @property
    def client(self) -> AsyncElasticsearch:
        """Ленивое создание ES-клиента."""
        if self._client is None:
            self._client = AsyncElasticsearch(
                self._config.es_url,
                basic_auth=("elastic", self._config.es_superuser_password),
                node_class=HttpxAsyncHttpNode,
            )
        return self._client

    async def search(self, query: str) -> list[int]:
        """Поиск документов по тексту. Возвращает список id."""
        index = self._config.es_documents_index_name
        response = await self.client.search(
            index=index,
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
        await self.client.delete(
            index=self._config.es_documents_index_name,
            id=str(doc_id),
        )

    async def create_index(self) -> None:
        """Создаёт индекс с маппингом. Идемпотентно."""
        await self.client.options(ignore_status=400).indices.create(
            index=self._config.es_documents_index_name,
            settings={"number_of_replicas": 0},
            mappings={
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "long"},
                    "text": {"type": "text"},
                },
            },
        )

    async def delete_index(self) -> None:
        """Удаляет индекс."""
        await self.client.options(ignore_status=[404]).indices.delete(
            index=self._config.es_documents_index_name,
        )

    async def index_documents(self, documents: list[dict]) -> None:
        """Массовая индексация документов.

        Каждый документ — словарь с ключами 'id' и 'text'.
        """
        actions = [
            {
                "_index": self._config.es_documents_index_name,
                "_id": str(doc["id"]),
                "_source": {
                    "id": doc["id"],
                    "text": doc["text"],
                },
            }
            for doc in documents
        ]
        await async_bulk(self.client, actions)

    async def close(self) -> None:
        """Закрывает ES-клиент."""
        if self._client is not None:
            await self._client.close()
            self._client = None
