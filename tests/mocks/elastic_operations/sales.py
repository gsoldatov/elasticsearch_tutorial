from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.mocks.elastic_operations import ElasticOperations


class ElasticSalesOperations:
    """Операции с тестовым индексом продаж."""

    def __init__(self, _es: "ElasticOperations") -> None:
        self._es = _es

    def count(self) -> int:
        result = self._es._client.count(
            index=self._es._config.es_sales_index_name,
        )
        return result["count"]

    def index_sale(
        self,
        date: str,
        region: str,
        product: str,
        units_sold: int,
        price: float,
        revenue: float,
    ) -> None:
        """Индексирует один документ продажи в тестовый индекс."""
        self._es._client.index(
            index=self._es._config.es_sales_index_name,
            document={
                "date": date,
                "region": region,
                "product": product,
                "units_sold": units_sold,
                "price": price,
                "revenue": revenue,
            },
            refresh=True,
        )
