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
