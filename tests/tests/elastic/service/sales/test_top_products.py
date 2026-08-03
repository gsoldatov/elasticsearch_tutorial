"""Тесты для ElasticSalesService.top_products."""
from datetime import date

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Пустой индекс — пустой список."""
    result = await elastic_service.sales.top_products()
    assert result == []


# ── базовая агрегация ──────────────────────────────────────────────────────


async def test_single_region_single_product(
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


async def test_single_region_multiple_products_top_n(
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


async def test_multiple_regions_each_with_top(
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


async def test_revenue_aggregation_sums_same_product(
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


async def test_default_n_is_10(
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


async def test_n_1_returns_only_top_product(
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(min_date=date(2025, 2, 1))

    assert len(result) == 1
    assert result[0].product == "телефон"
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(max_date=date(2025, 1, 31))

    assert len(result) == 1
    assert result[0].product == "ноутбук"
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
        product="телефон",
        units_sold=1,
        price=200.0,
        revenue=200.0,
    )

    result = await elastic_service.sales.top_products(regions=["Россия"])

    assert len(result) == 1
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
