from datetime import date
from typing import TYPE_CHECKING

from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticSalesServiceBase
from src.exceptions import internal_validation
from src.models.sales import Sale, SalesByMonthRegionItem

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticSalesService(ElasticSalesServiceBase):
    """Операции с продажами в ES: индексация, агрегации."""

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

    @internal_validation
    async def by_month_and_region(
        self,
        *,
        min_date: date | None = None,
        max_date: date | None = None,
        regions: list[str] | None = None,
        products: list[str] | None = None,
    ) -> list[SalesByMonthRegionItem]:
        """Агрегация выручки по месяцам и регионам с фильтрами."""
        index = self._es._config.es_sales_index_name

        filters: list[dict] = []

        if min_date is not None or max_date is not None:
            range_filter: dict = {}
            if min_date is not None:
                range_filter["gte"] = min_date.isoformat()
            if max_date is not None:
                range_filter["lte"] = max_date.isoformat()
            filters.append({"range": {"date": range_filter}})

        if regions:
            filters.append({"terms": {"region": regions}})

        if products:
            filters.append({"terms": {"product": products}})

        body: dict = {
            "size": 0,
            "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
            "aggs": {
                "by_month": {
                    "date_histogram": {
                        "field": "date",
                        "calendar_interval": "month",
                        "format": "yyyy-MM",
                        "min_doc_count": 1,
                    },
                    "aggs": {
                        "by_region": {
                            "terms": {
                                "field": "region",
                                "size": 10000,
                            },
                            "aggs": {
                                "total_revenue": {
                                    "sum": {"field": "revenue"},
                                },
                            },
                        },
                    },
                },
            },
        }

        response = await self.client.search(index=index, body=body)

        result: list[SalesByMonthRegionItem] = []
        for month_bucket in response["aggregations"]["by_month"]["buckets"]:
            month_key = month_bucket["key_as_string"]
            for region_bucket in month_bucket["by_region"]["buckets"]:
                result.append(
                    SalesByMonthRegionItem(
                        month=month_key,
                        region=region_bucket["key"],
                        revenue=region_bucket["total_revenue"]["value"],
                    )
                )

        # Сортировка: month ASC, region ASC
        result.sort(key=lambda item: (item.month, item.region))
        return result
