from typing import TYPE_CHECKING

from elasticsearch import NotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticDocumentsServiceBase
from src.models.document import Document

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticDocumentsService(ElasticDocumentsServiceBase):
    """Документные операции ES: поиск, удаление, индексация."""

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

    async def index_documents(self, documents: list[Document]) -> None:
        """Массовая индексация документов.

        Из модели Document извлекаются только id и text —
        остальные поля для поискового индекса не нужны.
        """
        actions = [
            {
                "_index": self._es._config.es_documents_index_name,
                "_id": str(doc.id),
                "_source": doc.model_dump(include={"id", "text"}),
            }
            for doc in documents
        ]
        await async_bulk(self.client, actions, refresh=self._es._refresh)
