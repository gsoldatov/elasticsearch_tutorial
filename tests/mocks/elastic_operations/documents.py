from typing import TYPE_CHECKING

from src.elastic import ElasticDocumentsService

if TYPE_CHECKING:
    from tests.mocks.elastic_operations import ElasticOperations


class ElasticDocumentsOperations:
    """Операции с тестовым индексом документов."""

    def __init__(self, _es: "ElasticOperations") -> None:
        self._es = _es

    # ── операции с индексом ─────────────────────────────────────────────

    def create_index(self) -> None:
        self._es._client.options(ignore_status=400).indices.create(
            index=self._es._index,
            **ElasticDocumentsService.INDEX_SETTINGS,
        )

    # ── операции с документами ──────────────────────────────────────────

    def index_document(self, doc_id: int, text: str) -> None:
        self._es._client.index(
            index=self._es._index,
            id=str(doc_id),
            document={"id": doc_id, "text": text},
            refresh="true",
        )

    def delete_document(self, doc_id: int) -> None:
        self._es._client.delete(
            index=self._es._index,
            id=str(doc_id),
            refresh="true",
        )

    def get_document(self, doc_id: int) -> dict | None:
        try:
            result = self._es._client.get(
                index=self._es._index,
                id=str(doc_id),
            )
            return result["_source"]
        except Exception:
            return None

    def refresh(self) -> None:
        self._es._client.indices.refresh(index=self._es._index)

    def count(self) -> int:
        result = self._es._client.count(index=self._es._index)
        return result["count"]

    def delete_all(self) -> None:
        self._es._client.options(ignore_status=404).delete_by_query(
            index=self._es._index,
            body={"query": {"match_all": {}}},
            refresh=True,
        )
