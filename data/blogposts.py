from datetime import datetime, timezone

from faker import Faker

from src.models.blogpost import Blogpost


def generate_blogposts(
    number: int = 1500,
    seed: int = 42,
    starting_id: int = 1,
) -> list[Blogpost]:
    """Генерирует список блогпостов с помощью Faker.

    Параметры:
        number: количество постов.
        seed: зерно для воспроизводимости.
        starting_id: первый числовой id (преобразуется в строку).
    """
    fake = Faker()
    fake.seed_instance(seed)

    # Случайные даты между началом предыдущего года и текущим моментом
    now = datetime.now(timezone.utc)
    start_date = datetime(now.year - 1, 1, 1, tzinfo=timezone.utc)

    blogposts: list[Blogpost] = []
    for i in range(number):
        blogposts.append(
            Blogpost(
                id=str(starting_id + i),
                title=fake.sentence(nb_words=6)[:256],
                text=fake.text(max_nb_chars=8192),
                tags=[fake.word() for _ in range(fake.random_int(min=0, max=10))],
                updated_at=fake.date_time_between(
                    start_date=start_date,
                    end_date=now,
                    tzinfo=timezone.utc,
                ),
            )
        )
    return blogposts
