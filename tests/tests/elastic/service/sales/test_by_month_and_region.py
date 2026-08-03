"""Тесты для ElasticSalesService.by_month_and_region."""
from datetime import date

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.by_month_and_region()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_single_month_single_region(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Один месяц, один регион — один элемент в результате."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=10,
        price=1000.0,
        revenue=10000.0,
    )

    result = await elastic_service.sales.by_month_and_region()

    assert len(result) == 1
    assert result[0].month == "2025-01"
    assert result[0].region == "Россия"
    assert result[0].revenue == 10000.0


async def test_multiple_sales_same_month_region_aggregated(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько продаж в одном месяце и регионе — revenue суммируется."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=1000.0,
        revenue=5000.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-20",
        region="Россия",
        product="телефон",
        units_sold=3,
        price=500.0,
        revenue=1500.0,
    )

    result = await elastic_service.sales.by_month_and_region()

    assert len(result) == 1
    assert result[0].revenue == 6500.0


async def test_multiple_months(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько месяцев — сортировка month ASC."""
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region()

    assert len(result) == 2
    assert result[0].month == "2025-01"
    assert result[0].revenue == 200.0
    assert result[1].month == "2025-02"
    assert result[1].revenue == 100.0


async def test_multiple_regions_sorted(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько регионов в одном месяце — сортировка region ASC."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Германия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region()

    assert len(result) == 2
    assert result[0].region == "Германия"
    assert result[0].revenue == 100.0
    assert result[1].region == "Россия"
    assert result[1].revenue == 200.0


# ── фильтры ────────────────────────────────────────────────────────────────


async def test_min_date_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """min_date отсекает более ранние продажи."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region(min_date=date(2025, 2, 1))

    assert len(result) == 1
    assert result[0].month == "2025-02"
    assert result[0].revenue == 200.0


async def test_max_date_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """max_date отсекает более поздние продажи."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region(max_date=date(2025, 1, 31))

    assert len(result) == 1
    assert result[0].month == "2025-01"
    assert result[0].revenue == 100.0


async def test_region_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Фильтр по регионам оставляет только указанные."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Германия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region(regions=["Россия"])

    assert len(result) == 1
    assert result[0].region == "Россия"
    assert result[0].revenue == 100.0


async def test_products_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Фильтр по продуктам оставляет только указанные."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук 1",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.by_month_and_region(products=["ноутбук 1"])

    assert len(result) == 1
    assert result[0].month == "2025-01"
    assert result[0].region == "Россия"
    assert result[0].revenue == 100.0


async def test_combined_filters(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Все фильтры одновременно."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Германия",
        product="ноутбук",
        units_sold=1,
        price=300.0,
        revenue=300.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="телефон",
        units_sold=1,
        price=400.0,
        revenue=400.0,
    )

    result = await elastic_service.sales.by_month_and_region(
        min_date=date(2025, 2, 1),
        regions=["Россия"],
        products=["ноутбук"],
    )

    assert len(result) == 1
    assert result[0].month == "2025-02"
    assert result[0].region == "Россия"
    assert result[0].revenue == 200.0
