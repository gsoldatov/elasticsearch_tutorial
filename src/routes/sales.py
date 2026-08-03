from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Query, Request
from pydantic import AfterValidator

from src.elastic import ElasticServiceBase
from src.models import SalesByMonthRegionItem, TopProductItem, validate_products_param, validate_region_param

router = APIRouter(tags=["sales"])

RegionQuery = Annotated[
    str | None,
    AfterValidator(validate_region_param),
    Query(description="Регионы через запятую, до 10"),
]

ProductsQuery = Annotated[
    str | None,
    AfterValidator(validate_products_param),
    Query(description="Продукты через запятую, до 10"),
]


@router.get(
    "/by_month_and_region",
    response_model=list[SalesByMonthRegionItem],
)
async def sales_by_month_and_region(
    request: Request,
    min_date: date | None = Query(None, description="Нижняя граница даты"),
    max_date: date | None = Query(None, description="Верхняя граница даты"),
    region: RegionQuery = None,
    products: ProductsQuery = None,
) -> list[SalesByMonthRegionItem]:
    """Агрегация выручки по месяцам и регионам с фильтрами."""
    region_list: list[str] | None = None
    if region is not None:
        region_list = [r.strip() for r in region.split(",") if r.strip()]

    products_list: list[str] | None = None
    if products is not None:
        products_list = [p.strip() for p in products.split(",") if p.strip()]

    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.sales.by_month_and_region(
        min_date=min_date,
        max_date=max_date,
        regions=region_list,
        products=products_list,
    )


@router.get(
    "/top_products",
    response_model=list[TopProductItem],
)
async def sales_top_products(
    request: Request,
    n: Annotated[
        int,
        Query(ge=1, le=100, description="Количество продуктов на регион"),
    ] = 10,
    min_date: date | None = Query(None, description="Нижняя граница даты"),
    max_date: date | None = Query(None, description="Верхняя граница даты"),
    region: RegionQuery = None,
) -> list[TopProductItem]:
    """Топ-n продуктов по выручке для каждого региона с фильтрами."""
    region_list: list[str] | None = None
    if region is not None:
        region_list = [r.strip() for r in region.split(",") if r.strip()]

    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.sales.top_products(
        n=n,
        min_date=min_date,
        max_date=max_date,
        regions=region_list,
    )
