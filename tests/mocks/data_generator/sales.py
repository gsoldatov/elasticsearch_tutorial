from datetime import datetime, timezone

from src.models.sales import Sale


class SalesDataGenerator:
    """Генератор тестовых Sale-объектов."""

    @staticmethod
    def sale(
        date: datetime | None = None,
        region: str = "Россия",
        product: str = "тестовый продукт",
        units_sold: int = 15,
        price: float = 100.0,
        revenue: float = 1500.0,
    ) -> Sale:
        return Sale(
            date=date if date is not None else datetime.now(timezone.utc),
            region=region,
            product=product,
            units_sold=units_sold,
            price=price,
            revenue=revenue,
        )
