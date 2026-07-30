from elasticsearch import Elasticsearch

from src.models.config import Config
from tests.mocks.elastic_operations.documents import ElasticDocumentsOperations


class ElasticOperations:
    """Операции с Elasticsearch для тестов."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = Elasticsearch(
            config.es_url,
            basic_auth=("elastic", config.es_superuser_password),
        )
        self._index = config.es_documents_index_name
        self.documents = ElasticDocumentsOperations(self)

    def close(self) -> None:
        """Закрывает sync-клиент ES."""
        self._client.close()

    def truncate_indices(self) -> None:
        """Удаляет все данные из всех тестовых индексов."""
        for index_name in self._config.es_indices.values():
            self._client.options(ignore_status=[404]).delete_by_query(
                index=index_name,
                body={"query": {"match_all": {}}},
                refresh=True,
            )

    def delete_index(self, index_name: str | None = None) -> None:
        """Удаляет указанный индекс."""
        self._client.options(ignore_status=[404]).indices.delete(
            index=index_name if index_name is not None else self._index,
        )
