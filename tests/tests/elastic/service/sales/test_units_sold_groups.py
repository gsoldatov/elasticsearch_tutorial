"""Тесты для ElasticSalesService.units_sold_groups."""
from datetime import date

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.units_sold_groups()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_single_sale_one_group(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Одна продажа — один интервал."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=1000.0,
        revenue=5000.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 1
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 5000.0


async def test_multiple_sales_same_interval_aggregated(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько продаж в одном интервале — revenue суммируется."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=3,
        price=100.0,
        revenue=300.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=7,
        price=200.0,
        revenue=1400.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 1
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 1700.0


async def test_multiple_intervals_sorted(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько интервалов — сортировка по возрастанию units_sold."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=25,
        price=100.0,
        revenue=2500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 2
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 1000.0
    assert result[1].units_sold == "21-30"
    assert result[1].total_revenue == 2500.0


async def test_sort_order_ascending(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Сортировка по возрастанию интервалов: 1-10, 11-20, 21-30, ..."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="планшет",
        units_sold=55,
        price=100.0,
        revenue=100.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=100.0,
        revenue=200.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=15,
        price=100.0,
        revenue=300.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="монитор",
        units_sold=35,
        price=100.0,
        revenue=400.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 4
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 200.0
    assert result[1].units_sold == "11-20"
    assert result[1].total_revenue == 300.0
    assert result[2].units_sold == "31-40"
    assert result[2].total_revenue == 400.0
    assert result[3].units_sold == "51-60"
    assert result[3].total_revenue == 100.0


async def test_boundary_value_10_in_first_interval(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """units_sold=10 попадает в интервал 1-10."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=10,
        price=100.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 1
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 1000.0


async def test_boundary_value_11_in_second_interval(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """units_sold=11 попадает в интервал 11-20."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=11,
        price=100.0,
        revenue=1100.0,
    )

    result = await elastic_service.sales.units_sold_groups()

    assert len(result) == 1
    assert result[0].units_sold == "11-20"
    assert result[0].total_revenue == 1100.0


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
        units_sold=5,
        price=100.0,
        revenue=500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="телефон",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups(min_date=date(2025, 2, 1))

    assert len(result) == 1
    assert result[0].total_revenue == 1000.0


async def test_max_date_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """max_date отсекает более поздние продажи."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=100.0,
        revenue=500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="телефон",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups(max_date=date(2025, 1, 31))

    assert len(result) == 1
    assert result[0].total_revenue == 500.0


async def test_region_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Фильтр по регионам оставляет только указанные."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=100.0,
        revenue=500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Германия",
        product="телефон",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups(regions=["Россия"])

    assert len(result) == 1
    assert result[0].total_revenue == 500.0


async def test_products_filter(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Фильтр по продуктам оставляет только указанные."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=100.0,
        revenue=500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )

    result = await elastic_service.sales.units_sold_groups(products=["ноутбук"])

    assert len(result) == 1
    assert result[0].total_revenue == 500.0


async def test_combined_filters(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Все фильтры одновременно."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=100.0,
        revenue=500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="ноутбук",
        units_sold=5,
        price=200.0,
        revenue=1000.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Россия",
        product="телефон",
        units_sold=5,
        price=300.0,
        revenue=1500.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-02-15",
        region="Германия",
        product="ноутбук",
        units_sold=5,
        price=400.0,
        revenue=2000.0,
    )

    result = await elastic_service.sales.units_sold_groups(
        min_date=date(2025, 2, 1),
        regions=["Россия"],
        products=["ноутбук"],
    )

    assert len(result) == 1
    assert result[0].units_sold == "1-10"
    assert result[0].total_revenue == 1000.0
