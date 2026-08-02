from copy import deepcopy

from elasticsearch import NotFoundError as EsNotFoundError

from src.elastic.service.migrations.revisions.base import RevisionBase
from src.elastic.service.migrations.revisions.r_0002_blogposts import (
    Revision0002Blogposts,
)


class Revision0003BlogpostTagsSubfield(RevisionBase):
    """Добавление сабфилда tags._as_you_type (search_as_you_type)."""

    _INDEX_SETTINGS_V1 = Revision0002Blogposts._INDEX_SETTINGS

    _INDEX_SETTINGS_V2 = deepcopy(Revision0002Blogposts._INDEX_SETTINGS)
    _INDEX_SETTINGS_V2["mappings"]["properties"]["tags"] = {
        "type": "keyword",
        "fields": {
            "_as_you_type": {"type": "search_as_you_type"},
        },
    }

    @property
    def _index_name(self) -> str:
        return self._es._config.es_blogposts_index_name

    @property
    def _v1(self) -> str:
        return f"{self._index_name}_v1"

    @property
    def _v2(self) -> str:
        return f"{self._index_name}_v2"

    @property
    def _pipeline_name(self) -> str:
        return f"{self._index_name}_pipeline"

    def _make_index_settings(self, mapping: dict) -> dict:
        """Оборачивает маппинг в настройки индекса с дефолтным pipeline."""
        settings = {
            "settings": {
                **mapping["settings"],
                "default_pipeline": self._pipeline_name,
            },
            "mappings": mapping["mappings"],
        }
        return settings

    async def _ensure_pipeline_exists(self) -> None:
        """Проверяет, что pipeline существует (должен быть создан в r_0002)."""
        try:
            await self._es.client.ingest.get_pipeline(id=self._pipeline_name)
        except EsNotFoundError:
            raise ValueError(
                f"Pipeline '{self._pipeline_name}' не найден — "
                f"миграция 0002 не была применена перед 0003."
            ) from None

    async def _create_pipeline(self) -> None:
        """Создаёт или перезаписывает pipeline (идемпотентно)."""
        await self._es.client.ingest.put_pipeline(
            id=self._pipeline_name,
            body={
                "description": (
                    "Устанавливает updated_at, "
                    "если значение не передано явно"
                ),
                "processors": [
                    {
                        "set": {
                            "field": "updated_at",
                            "value": "{{{_ingest.timestamp}}}",
                            "override": False,
                        },
                    },
                ],
            },
        )

    async def upgrade(self) -> None:
        """Создаёт _v2 с сабфилдом tags._text, reindex, swap alias, удаляет _v1."""
        await self._ensure_pipeline_exists()

        # 1. Создаём _v2
        await self._es.client.indices.create(
            index=self._v2,
            **self._make_index_settings(self._INDEX_SETTINGS_V2),
        )

        # 2. Reindex _v1 → _v2
        await self._es.client.reindex(
            body={
                "source": {"index": self._v1},
                "dest": {"index": self._v2},
            },
            refresh=True,
        )

        # 3. Atom swap alias: снять с _v1, накинуть на _v2
        await self._es.client.indices.update_aliases(
            body={
                "actions": [
                    {"remove": {"index": self._v1, "alias": self._index_name}},
                    {"add": {"index": self._v2, "alias": self._index_name}},
                ],
            },
        )

        # 4. Удалить старый индекс
        await self._es.client.indices.delete(index=self._v1)

    async def downgrade(self) -> None:
        """Создаёт _v1 без сабфилда, reindex из _v2, swap alias, удаляет _v2."""
        # Если _v2 уже нет — downgrade полностью применён, нечего делать
        if not await self._es.client.indices.exists(index=self._v2):
            return

        await self._create_pipeline()

        # 1. Создаём _v1 со старым маппингом (если ещё не существует)
        if not await self._es.client.indices.exists(index=self._v1):
            await self._es.client.indices.create(
                index=self._v1,
                **self._make_index_settings(self._INDEX_SETTINGS_V1),
            )

        # 2. Reindex _v2 → _v1
        await self._es.client.reindex(
            body={
                "source": {"index": self._v2},
                "dest": {"index": self._v1},
            },
            refresh=True,
        )

        # 3. Atom swap alias: снять с _v2, накинуть на _v1
        await self._es.client.indices.update_aliases(
            body={
                "actions": [
                    {"remove": {"index": self._v2, "alias": self._index_name}},
                    {"add": {"index": self._v1, "alias": self._index_name}},
                ],
            },
        )

        # 4. Удалить _v2
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._v2,
        )
