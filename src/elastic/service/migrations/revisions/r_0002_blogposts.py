from src.elastic.service.migrations.revisions.base import RevisionBase


class Revision0002Blogposts(RevisionBase):
    """Создание индекса блогпостов и ingest pipeline."""

    _INDEX_SETTINGS = {
        "settings": {"number_of_replicas": 0},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "title": {"type": "text", "analyzer": "standard"},
                "text": {"type": "text", "analyzer": "standard"},
                "tags": {"type": "keyword"},
                "updated_at": {"type": "date"},
            },
        },
    }

    @property
    def _index_name(self) -> str:
        return self._es._config.es_blogposts_index_name

    @property
    def _real_index(self) -> str:
        return f"{self._index_name}_v1"

    @property
    def _pipeline_name(self) -> str:
        return f"{self._index_name}_pipeline"

    async def upgrade(self) -> None:
        """Создаёт pipeline, индекс и alias."""
        # 1. Ingest pipeline — ставит updated_at только при создании
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
                            # Значение по умолчанию добавляется только если
                            # updated_at не передано в новой версии документа
                            "override": False,
                        },
                    },
                ],
            },
        )

        # 2. Реальный индекс с default_pipeline
        settings = dict(self._INDEX_SETTINGS)
        settings["settings"] = {
            **settings["settings"],
            "default_pipeline": self._pipeline_name,
        }
        await self._es.client.indices.create(
            index=self._real_index,
            **settings,
        )

        # 3. Alias
        await self._es.client.indices.put_alias(
            index=self._real_index,
            name=self._index_name,
        )

    async def downgrade(self) -> None:
        """Удаляет alias, индекс, pipeline — идемпотентно."""
        # Сначала удаляем alias и индекс (снимаем ссылку на pipeline)
        await self._es.client.options(ignore_status=[404]).indices.delete_alias(
            index="_all",
            name=self._index_name,
        )
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._real_index,
        )
        # Теперь pipeline можно удалить
        await self._es.client.options(ignore_status=[404]).ingest.delete_pipeline(
            id=self._pipeline_name,
        )
