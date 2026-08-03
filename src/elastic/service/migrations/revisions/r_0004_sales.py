from src.elastic.service.migrations.revisions.base import RevisionBase


class Revision0004Sales(RevisionBase):
    """Создание индекса продаж."""

    _INDEX_SETTINGS = {
        "settings": {"number_of_replicas": 0},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "date": {"type": "date"},
                "region": {"type": "keyword"},
                "product": {"type": "keyword"},
                "units_sold": {"type": "integer"},
                "price": {"type": "scaled_float", "scaling_factor": 100},
                "revenue": {"type": "scaled_float", "scaling_factor": 100},
            },
        },
    }

    @property
    def _index_name(self) -> str:
        return self._es._config.es_sales_index_name

    @property
    def _real_index(self) -> str:
        return f"{self._index_name}_v1"

    async def upgrade(self) -> None:
        """Создаёт индекс и alias."""
        await self._es.client.indices.create(
            index=self._real_index,
            **self._INDEX_SETTINGS,
        )
        await self._es.client.indices.put_alias(
            index=self._real_index,
            name=self._index_name,
        )

    async def downgrade(self) -> None:
        """Удаляет alias и индекс — идемпотентно."""
        await self._es.client.options(ignore_status=[404]).indices.delete_alias(
            index="_all",
            name=self._index_name,
        )
        await self._es.client.options(ignore_status=[404]).indices.delete(
            index=self._real_index,
        )
