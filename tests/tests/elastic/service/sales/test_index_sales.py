from datetime import datetime, timezone

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


async def test_index_sales_bulk(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Массовая индексация продаж."""
    sales = [
        data_generator.sales.sale(
            date=datetime(2025, 6, i, tzinfo=timezone.utc),
            region=f"Регион {i}",
            product=f"Продукт {i}",
            units_sold=i * 10,
            price=float(i * 100),
            revenue=float(i * 1000),
        )
        for i in range(1, 11)
    ]
    await elastic_service.sales.index_sales(sales)

    assert elastic_operations.sales.count() == 10
