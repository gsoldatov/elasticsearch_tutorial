from elasticsearch import Elasticsearch

from src.elastic.service import ElasticService


class ElasticOperations:
    """Операции с тестовым индексом Elasticsearch (синхронные)."""

    def __init__(self, client: Elasticsearch, index_name: str) -> None:
        self._client = client
        self._index = index_name

    # ── index operations ───────────────────────────────────────────────

    def create_index(self) -> None:
        self._client.options(ignore_status=400).indices.create(
            index=self._index,
            **ElasticService.INDEX_SETTINGS,
        )

    def delete_index(self, index_name: str | None = None) -> None:
        self._client.options(ignore_status=[404]).indices.delete(
            index=index_name if index_name is not None else self._index,
        )

    # ── document operations ────────────────────────────────────────────

    def index_document(self, doc_id: int, text: str) -> None:
        self._client.index(
            index=self._index,
            id=str(doc_id),
            document={"id": doc_id, "text": text},
            refresh="true",
        )

    def delete_document(self, doc_id: int) -> None:
        self._client.delete(
            index=self._index,
            id=str(doc_id),
            refresh="true",
        )

    def get_document(self, doc_id: int) -> dict | None:
        try:
            result = self._client.get(
                index=self._index,
                id=str(doc_id),
            )
            return result["_source"]
        except Exception:
            return None

    def refresh(self) -> None:
        self._client.indices.refresh(index=self._index)

    def count(self) -> int:
        result = self._client.count(index=self._index)
        return result["count"]

    def delete_all(self) -> None:
        self._client.options(ignore_status=404).delete_by_query(
            index=self._index,
            body={"query": {"match_all": {}}},
            refresh=True,
        )
