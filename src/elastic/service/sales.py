from typing import TYPE_CHECKING

from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticSalesServiceBase
from src.models.sales import Sale

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticSalesService(ElasticSalesServiceBase):
    """Операции с продажами в ES: индексация."""

    def __init__(self, _es: "ElasticService") -> None:
        self._es = _es

    @property
    def client(self):
        return self._es.client

    async def index_sales(self, sales: list[Sale]) -> None:
        """Массовая индексация продаж."""
        actions = [
            {
                "_index": self._es._config.es_sales_index_name,
                "_source": sale.to_dict(),
            }
            for sale in sales
        ]
        await async_bulk(self.client, actions, refresh=self._es._refresh)
