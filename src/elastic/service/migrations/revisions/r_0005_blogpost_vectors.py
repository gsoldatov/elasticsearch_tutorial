from copy import deepcopy

from elasticsearch import NotFoundError as EsNotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.service.migrations.revisions.base import RevisionBase
from src.elastic.service.migrations.revisions.r_0003_blogpost_tags_subfield import (
    Revision0003BlogpostTagsSubfield,
)

# ── Конфигурация dense_vector ────────────────────────────────────────────

# ES 7.17 поддерживает только type и dims для dense_vector;
# similarity, index, index_options — фичи 8.x
_VECTOR_FIELD = {
    "type": "dense_vector",
    "dims": 384,
}


class Revision0005BlogpostVectors(RevisionBase):
    """Добавление dense_vector в блогпосты и создание индекса чанков."""

    # Маппинг _v2 (из r_0003, с сабфилдом tags._as_you_type)
    _INDEX_SETTINGS_V2 = Revision0003BlogpostTagsSubfield._INDEX_SETTINGS_V2

    # Маппинг _v3 — с title_vector
    _INDEX_SETTINGS_V3 = deepcopy(Revision0003BlogpostTagsSubfield._INDEX_SETTINGS_V2)
    _INDEX_SETTINGS_V3["mappings"]["properties"]["title_vector"] = _VECTOR_FIELD

    # Маппинг индекса чанков
    _CHUNKS_SETTINGS = {
        "settings": {"number_of_replicas": 0},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "blogpost_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "chunk_text": {"type": "text", "analyzer": "standard"},
                "chunk_vector": _VECTOR_FIELD,
            },
        },
    }

    @property
    def _index_name(self) -> str:
        return self._es._config.es_blogposts_index_name

    @property
    def _chunks_index_name(self) -> str:
        return self._es._config.es_blogposts_text_chunks_index_name

    @property
    def _v2(self) -> str:
        return f"{self._index_name}_v2"

    @property
    def _v3(self) -> str:
        return f"{self._index_name}_v3"

    @property
    def _pipeline_name(self) -> str:
        return f"{self._index_name}_pipeline"

    def _make_index_settings(self, mapping: dict) -> dict:
        """Оборачивает маппинг в настройки индекса с дефолтным pipeline."""
        return {
            "settings": {
                **mapping["settings"],
                "default_pipeline": self._pipeline_name,
            },
            "mappings": mapping["mappings"],
        }

    async def _ensure_pipeline_exists(self) -> None:
        """Проверяет, что pipeline существует."""
        try:
            await self._es.client.ingest.get_pipeline(id=self._pipeline_name)
        except EsNotFoundError:
            raise ValueError(
                f"Pipeline '{self._pipeline_name}' не найден — "
                f"миграция 0002 не была применена перед 0005."
            ) from None

    async def _ensure_v2_exists(self) -> None:
        """Проверяет, что _v2 существует."""
        if not await self._es.client.indices.exists(index=self._v2):
            raise ValueError(
                f"Индекс '{self._v2}' не найден — "
                f"миграция 0002 не была применена перед 0005."
            ) from None

    # ── upgrade ──────────────────────────────────────────────────────────

    async def upgrade(self) -> None:
        """Создаёт _v3 с title_vector и индекс чанков, переносит данные,
        генерирует эмбеддинги."""
        await self._ensure_pipeline_exists()
        await self._ensure_v2_exists()

        # 1. Создаём _v3 и индекс чанков
        await self._es.client.indices.create(
            index=self._v3,
            **self._make_index_settings(self._INDEX_SETTINGS_V3),
        )
        await self._es.client.indices.create(
            index=self._chunks_index_name,
            **self._CHUNKS_SETTINGS,
        )

        # 2. Читаем все документы из _v2 через scroll, генерируем эмбеддинги,
        #    пишем в _v3 (с title_vector) и в индекс чанков
        await self._migrate_data_from_v2()

        # 3. Atom swap alias: снять с _v2, накинуть на _v3
        await self._es.client.indices.update_aliases(
            body={
                "actions": [
                    {"remove": {"index": self._v2, "alias": self._index_name}},
                    {"add": {"index": self._v3, "alias": self._index_name}},
                ],
            },
        )

        # 4. Удалить старый индекс
        await self._es.client.indices.delete(index=self._v2)

    async def _migrate_data_from_v2(self) -> None:
        """Читает документы из _v2, генерирует эмбеддинги,
        пишет в _v3 и индекс чанков батчами."""
        batch_size = 1000

        # Инициализируем scroll
        scroll_resp = await self._es.client.search(
            index=self._v2,
            body={
                "query": {"match_all": {}},
                "size": batch_size,
            },
            scroll="30m",
        )

        scroll_id = scroll_resp.get("_scroll_id")
        hits = scroll_resp["hits"]["hits"]

        try:
            while hits:
                blogpost_actions: list[dict] = []
                chunk_actions: list[dict] = []

                for hit in hits:
                    doc_id = hit["_id"]
                    source = hit["_source"]
                    title = source.get("title", "")
                    text = source.get("text", "")

                    # Получаем эмбеддинги
                    title_vector, chunks = (
                        await self._es.blogposts.embeddings.get_embeddings(
                            blogpost_id=doc_id,
                            title=title,
                            text=text,
                        )
                    )

                    # Документ для _v3: копия исходного + title_vector
                    doc = dict(source)
                    if title_vector is not None:
                        doc["title_vector"] = title_vector
                    blogpost_actions.append({
                        "_index": self._v3,
                        "_id": doc_id,
                        "_source": doc,
                    })

                    # Чанки
                    for chunk in chunks:
                        chunk_actions.append({
                            "_index": self._chunks_index_name,
                            "_source": chunk.model_dump(mode="json"),
                        })

                # Bulk-вставка в _v3
                if blogpost_actions:
                    await async_bulk(
                        self._es.client, blogpost_actions,
                        refresh=True,
                    )

                # Bulk-вставка чанков
                if chunk_actions:
                    await async_bulk(
                        self._es.client, chunk_actions,
                        refresh=True,
                    )

                # Следующая страница scroll
                scroll_resp = await self._es.client.scroll(
                    scroll_id=scroll_id,
                    scroll="30m",
                )
                scroll_id = scroll_resp.get("_scroll_id")
                hits = scroll_resp["hits"]["hits"]
        finally:
            # Очищаем scroll-контекст
            if scroll_id:
                await self._es.client.options(ignore_status=[404]).clear_scroll(
                    scroll_id=scroll_id,
                )

    # ── downgrade ────────────────────────────────────────────────────────

    async def downgrade(self) -> None:
        """Создаёт _v2 без векторов, reindex из _v3, swap alias,
        удаляет _v3 и индекс чанков."""
        # Если _v3 уже нет — downgrade полностью применён
        if not await self._es.client.indices.exists(index=self._v3):
            return

        # 1. Создаём _v2 со старым маппингом (если ещё не существует)
        if not await self._es.client.indices.exists(index=self._v2):
            await self._es.client.indices.create(
                index=self._v2,
                **self._make_index_settings(self._INDEX_SETTINGS_V2),
            )

        # 2. Reindex _v3 → _v2 (векторы теряются — их нет в маппинге _v2)
        await self._es.client.reindex(
            body={
                "source": {"index": self._v3},
                "dest": {"index": self._v2},
            },
            refresh=True,
        )

        # 3. Atom swap alias: снять с _v3, накинуть на _v2
        await self._es.client.indices.update_aliases(
            body={
                "actions": [
                    {"remove": {"index": self._v3, "alias": self._index_name}},
                    {"add": {"index": self._v2, "alias": self._index_name}},
                ],
            },
        )

        # 4. Удалить _v3 и индекс чанков
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._v3,
        )
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._chunks_index_name,
        )
