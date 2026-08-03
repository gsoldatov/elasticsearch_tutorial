from dataclasses import dataclass
from datetime import datetime


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
