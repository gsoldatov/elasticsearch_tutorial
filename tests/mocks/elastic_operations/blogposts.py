from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.mocks.elastic_operations import ElasticOperations


class ElasticBlogpostsOperations:
    """Операции с тестовым индексом блогпостов."""

    def __init__(self, _es: "ElasticOperations") -> None:
        self._es = _es

    # ── операции с блогпостами ──────────────────────────────────────────

    def index_blogpost(
        self,
        blogpost_id: str,
        title: str,
        text: str,
        tags: list[str],
        updated_at: str,
    ) -> None:
        self._es._client.index(
            index=self._es._config.es_blogposts_index_name,
            id=blogpost_id,
            document={
                "title": title,
                "text": text,
                "tags": tags,
                "updated_at": updated_at,
            },
            refresh="true",
        )

    def delete_blogpost(self, blogpost_id: str) -> None:
        self._es._client.delete(
            index=self._es._config.es_blogposts_index_name,
            id=blogpost_id,
            refresh="true",
        )

    def get_blogpost(self, blogpost_id: str) -> dict | None:
        try:
            result = self._es._client.get(
                index=self._es._config.es_blogposts_index_name,
                id=blogpost_id,
            )
            return result["_source"]
        except Exception:
            return None

    def count(self) -> int:
        result = self._es._client.count(
            index=self._es._config.es_blogposts_index_name,
        )
        return result["count"]
