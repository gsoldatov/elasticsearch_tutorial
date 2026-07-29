from src.elastic.service.migrations.revisions.base import RevisionBase


class Revision0001Documents(RevisionBase):
    """Создание индекса документов с маппингом."""

    _INDEX_SETTINGS = {
        "settings": {"number_of_replicas": 0},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "text": {"type": "text", "analyzer": "russian"},
            },
        },
    }

    async def upgrade(self) -> None:
        """Создаёт индекс документов."""
        await self._es.client.indices.create(
            index=self._es._config.es_documents_index_name,
            **self._INDEX_SETTINGS,
        )

    async def downgrade(self) -> None:
        """Удаляет индекс документов."""
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._es._config.es_documents_index_name,
        )
