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

    def index_blogpost_with_vectors(
        self,
        blogpost_id: str,
        title: str,
        text: str,
        tags: list[str],
        updated_at: str,
        title_vector: list[float] | None = None,
        chunks: list[dict] | None = None,
    ) -> None:
        """Индексирует блогпост с опциональным title_vector и чанками.

        Используется в тестах векторного поиска для размещения документов
        с известными векторами — это позволяет контролировать
        косинусное сходство с вектором запроса.
        """
        doc: dict = {
            "title": title,
            "text": text,
            "tags": tags,
            "updated_at": updated_at,
        }
        if title_vector is not None:
            doc["title_vector"] = title_vector

        self._es._client.index(
            index=self._es._config.es_blogposts_index_name,
            id=blogpost_id,
            document=doc,
            refresh="true",
        )

        if chunks:
            chunks_index = self._es._config.es_blogposts_text_chunks_index_name
            for chunk in chunks:
                self._es._client.index(
                    index=chunks_index,
                    document=chunk,
                    refresh="true",
                )
