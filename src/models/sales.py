from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _validate_csv_param(
    v: str | None,
    param_name: str,
    *,
    max_count: int,
    min_length: int,
    max_length: int,
) -> str | None:
    """Валидирует строку из query-параметра: разбивает по запятой
    и проверяет каждый элемент."""
    if v is None:
        return v
    items = [t.strip() for t in v.split(",")]
    if len(items) > max_count:
        raise ValueError(
            f"Значение параметра {param_name} должно содержать не более "
            f"{max_count} элементов"
        )
    for item in items:
        if len(item) < min_length or len(item) > max_length:
            raise ValueError(
                f"Длина каждого элемента {param_name} должна быть от "
                f"{min_length} до {max_length} символов"
            )
    return v


def validate_region_param(v: str | None) -> str | None:
    """Валидирует строку регионов из query-параметра."""
    return _validate_csv_param(v, "region", max_count=10, min_length=1, max_length=64)


def validate_products_param(v: str | None) -> str | None:
    """Валидирует строку продуктов из query-параметра."""
    return _validate_csv_param(v, "products", max_count=10, min_length=1, max_length=64)


# ── Dataclass ──────────────────────────────────────────────────────────────


@dataclass
class Sale:
    """Полное представление документа о продаже."""

    date: datetime
    region: str
    product: str
    units_sold: int
    price: float
    revenue: float

    def to_dict(self) -> dict:
        """Сериализует Sale в словарь для ES-индексации."""
        return {
            "date": self.date.isoformat(),
            "region": self.region,
            "product": self.product,
            "units_sold": self.units_sold,
            "price": self.price,
            "revenue": self.revenue,
        }


# ── Pydantic-модели ────────────────────────────────────────────────────────


class SalesByMonthRegionItem(BaseModel):
    """Элемент результата агрегации: выручка по месяцу и региону."""

    model_config = ConfigDict(strict=True)

    month: str = Field(description="Месяц в формате yyyy-MM")
    region: str
    revenue: float = Field(description="Суммарная выручка")


class TopProductItem(BaseModel):
    """Элемент результата агрегации: топ продуктов по регионам."""

    model_config = ConfigDict(strict=True)

    region: str
    product: str
    revenue: float = Field(description="Суммарная выручка")


class UnitsSoldGroupItem(BaseModel):
    """Элемент результата агрегации: выручка по интервалам units_sold."""

    model_config = ConfigDict(strict=True)

    units_sold: str = Field(description="Интервал единиц продаж, например 1-10")
    total_revenue: float = Field(description="Суммарная выручка")
