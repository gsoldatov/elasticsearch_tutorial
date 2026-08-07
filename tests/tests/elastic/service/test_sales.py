"""Тесты ElasticSalesService."""

from datetime import date, datetime, timezone

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ══════════════════════════════════════════════════════════════════════════════
# by_month_and_region
# ══════════════════════════════════════════════════════════════════════════════


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_by_month_and_region_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.by_month_and_region()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_by_month_and_region_single_month_single_region(
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


async def test_by_month_and_region_multiple_sales_same_month_region_aggregated(
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


async def test_by_month_and_region_multiple_months(
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


async def test_by_month_and_region_multiple_regions_sorted(
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


async def test_by_month_and_region_min_date_filter(
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


async def test_by_month_and_region_max_date_filter(
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


async def test_by_month_and_region_region_filter(
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


async def test_by_month_and_region_products_filter(
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


async def test_by_month_and_region_combined_filters(
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


# ══════════════════════════════════════════════════════════════════════════════
# index_sales
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# top_products
# ══════════════════════════════════════════════════════════════════════════════


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_top_products_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.top_products()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_top_products_single_region_single_product(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Один регион, один продукт — один элемент в результате."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=10,
        price=1000.0,
        revenue=10000.0,
    )

    result = await elastic_service.sales.top_products()

    assert len(result) == 1
    assert result[0].region == "Россия"
    assert result[0].product == "ноутбук"
    assert result[0].revenue == 10000.0


async def test_top_products_single_region_multiple_products_top_n(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Один регион, несколько продуктов — возвращаются топ-n по revenue."""
    elastic_operations.sales.index_sale(
        date="2025-01-10",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=1000.0,
        revenue=1000.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=2,
        price=800.0,
        revenue=1600.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-20",
        region="Россия",
        product="планшет",
        units_sold=1,
        price=500.0,
        revenue=500.0,
    )

    result = await elastic_service.sales.top_products(n=2)

    assert len(result) == 2
    assert result[0].product == "телефон"
    assert result[0].revenue == 1600.0
    assert result[1].product == "ноутбук"
    assert result[1].revenue == 1000.0


async def test_top_products_multiple_regions_each_with_top(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько регионов — каждый со своим топом, сортировка region ASC."""
    # Россия: ноутбук 1000, телефон 800, планшет 500
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=1000.0,
        revenue=1000.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=1,
        price=800.0,
        revenue=800.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="планшет",
        units_sold=1,
        price=500.0,
        revenue=500.0,
    )
    # Германия: телефон 1200, ноутбук 900
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Германия",
        product="телефон",
        units_sold=1,
        price=1200.0,
        revenue=1200.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Германия",
        product="ноутбук",
        units_sold=1,
        price=900.0,
        revenue=900.0,
    )

    result = await elastic_service.sales.top_products(n=2)

    assert len(result) == 4
    # Сортировка: region ASC, revenue DESC внутри региона
    assert result[0].region == "Германия"
    assert result[0].product == "телефон"
    assert result[0].revenue == 1200.0
    assert result[1].region == "Германия"
    assert result[1].product == "ноутбук"
    assert result[1].revenue == 900.0
    assert result[2].region == "Россия"
    assert result[2].product == "ноутбук"
    assert result[2].revenue == 1000.0
    assert result[3].region == "Россия"
    assert result[3].product == "телефон"
    assert result[3].revenue == 800.0


async def test_top_products_revenue_aggregation_sums_same_product(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Несколько продаж одного продукта — revenue суммируется."""
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
        product="ноутбук",
        units_sold=3,
        price=1000.0,
        revenue=3000.0,
    )

    result = await elastic_service.sales.top_products()

    assert len(result) == 1
    assert result[0].product == "ноутбук"
    assert result[0].revenue == 8000.0


async def test_top_products_default_n_is_10(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """По умолчанию n=10 — возвращает до 10 продуктов на регион."""
    for i in range(15):
        elastic_operations.sales.index_sale(
            date="2025-01-15",
            region="Россия",
            product=f"продукт {i:02d}",
            units_sold=1,
            price=float(100 + i),
            revenue=float(100 + i),
        )

    result = await elastic_service.sales.top_products()

    assert len(result) == 10


async def test_top_products_n_1_returns_only_top_product(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """n=1 — только топ-продукт на регион."""
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="ноутбук",
        units_sold=1,
        price=1000.0,
        revenue=1000.0,
    )
    elastic_operations.sales.index_sale(
        date="2025-01-15",
        region="Россия",
        product="телефон",
        units_sold=1,
        price=500.0,
        revenue=500.0,
    )

    result = await elastic_service.sales.top_products(n=1)

    assert len(result) == 1
    assert result[0].product == "ноутбук"
    assert result[0].revenue == 1000.0


# ── фильтры ────────────────────────────────────────────────────────────────


async def test_top_products_min_date_filter(
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(min_date=date(2025, 2, 1))

    assert len(result) == 1
    assert result[0].product == "телефон"
    assert result[0].revenue == 200.0


async def test_top_products_max_date_filter(
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(max_date=date(2025, 1, 31))

    assert len(result) == 1
    assert result[0].product == "ноутбук"
    assert result[0].revenue == 100.0


async def test_top_products_region_filter(
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(regions=["Россия"])

    assert len(result) == 1
    assert result[0].region == "Россия"
    assert result[0].revenue == 100.0


async def test_top_products_combined_filters(
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
        product="телефон",
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
        product="планшет",
        units_sold=1,
        price=400.0,
        revenue=400.0,
    )

    result = await elastic_service.sales.top_products(
        n=2,
        min_date=date(2025, 2, 1),
        regions=["Россия"],
    )

    assert len(result) == 2
    assert result[0].region == "Россия"
    assert result[0].product == "планшет"
    assert result[0].revenue == 400.0
    assert result[1].region == "Россия"
    assert result[1].product == "телефон"
    assert result[1].revenue == 200.0


# ══════════════════════════════════════════════════════════════════════════════
# units_sold_groups
# ══════════════════════════════════════════════════════════════════════════════


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_units_sold_groups_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.units_sold_groups()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_units_sold_groups_single_sale_one_group(
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


async def test_units_sold_groups_multiple_sales_same_interval_aggregated(
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


async def test_units_sold_groups_multiple_intervals_sorted(
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


async def test_units_sold_groups_sort_order_ascending(
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


async def test_units_sold_groups_boundary_value_10_in_first_interval(
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


async def test_units_sold_groups_boundary_value_11_in_second_interval(
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


async def test_units_sold_groups_min_date_filter(
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


async def test_units_sold_groups_max_date_filter(
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


async def test_units_sold_groups_region_filter(
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


async def test_units_sold_groups_products_filter(
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


async def test_units_sold_groups_combined_filters(
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
