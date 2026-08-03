import random
from datetime import datetime, timezone

from faker import Faker

from src.models.sales import Sale


def generate_sales(
    number: int = 10000,
    seed: int = 42,
) -> list[Sale]:
    """Генерирует список продаж.

    Параметры:
        number: количество записей.
        seed: зерно для воспроизводимости.
    """
    fake = Faker()
    fake.seed_instance(seed)
    random.seed(seed)

    # Диапазон дат: с начала предыдущего года до вчерашнего дня
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today.replace(day=today.day - 1) if today.day > 1 else today.replace(month=today.month - 1, day=28)
    start_date = datetime(today.year - 1, 1, 1, tzinfo=timezone.utc)

    # Регионы: 5-10 уникальных стран
    regions_count = random.randint(5, 10)
    regions = [fake.unique.country() for _ in range(regions_count)]

    # Продукты: 50-100 уникальных названий с базовой ценой и допустимым отклонением
    products_count = random.randint(50, 100)
    products: list[dict] = []
    for _ in range(products_count):
        name_parts = fake.words(nb=random.randint(1, 2))
        name = " ".join(name_parts)
        base_price = round(random.uniform(100, 10000), 2)
        deviation_pct = round(random.uniform(0.05, 0.30), 2)
        products.append({
            "name": name,
            "base_price": base_price,
            "deviation_pct": deviation_pct,
        })

    sales: list[Sale] = []
    for _ in range(number):
        product = random.choice(products)
        # Цена продажи: нормальное распределение вокруг базовой цены,
        # обрезанное в пределах допустимого отклонения
        sigma = product["base_price"] * product["deviation_pct"] / 3
        sale_price = max(
            product["base_price"] * (1 - product["deviation_pct"]),
            min(
                product["base_price"] * (1 + product["deviation_pct"]),
                round(random.gauss(product["base_price"], sigma), 2),
            ),
        )
        # Количество: гамма-распределение, пик в 10-29
        units_sold = max(1, min(200, round(random.gammavariate(5, 4))))
        revenue = round(units_sold * sale_price, 2)

        sales.append(
            Sale(
                date=fake.date_time_between(
                    start_date=start_date,
                    end_date=yesterday,
                    tzinfo=timezone.utc,
                ),
                region=random.choice(regions),
                product=product["name"],
                units_sold=units_sold,
                price=sale_price,
                revenue=revenue,
            )
        )
    return sales
