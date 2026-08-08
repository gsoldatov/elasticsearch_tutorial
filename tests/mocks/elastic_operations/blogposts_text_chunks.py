from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.mocks.elastic_operations import ElasticOperations


class ElasticBlogpostsTextChunksOperations:
    """Операции с тестовым индексом чанков текста блогпостов."""

    def __init__(self, _es: "ElasticOperations") -> None:
        self._es = _es

    def count(self) -> int:
        result = self._es._client.count(
            index=self._es._config.es_blogposts_text_chunks_index_name,
        )
        return result["count"]

    def get_all(self) -> list[dict]:
        """Возвращает все чанки из индекса."""
        result = self._es._client.search(
            index=self._es._config.es_blogposts_text_chunks_index_name,
            body={"query": {"match_all": {}}},
        )
        return [hit["_source"] for hit in result["hits"]["hits"]]
