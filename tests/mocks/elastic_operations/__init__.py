from elasticsearch import Elasticsearch

from tests.mocks.elastic_operations.documents import ElasticDocumentsOperations


class ElasticOperations:
    """Операций с Elasticsearch."""

    def __init__(self, client: Elasticsearch, index_name: str) -> None:
        self._client = client
        self._index = index_name
        self.documents = ElasticDocumentsOperations(self)

    def delete_index(self, index_name: str | None = None) -> None:
        """Удаляет указанный индекс."""
        self._client.options(ignore_status=[404]).indices.delete(
            index=index_name if index_name is not None else self._index,
        )
