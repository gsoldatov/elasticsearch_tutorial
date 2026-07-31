import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from data.blogposts import generate_blogposts
from src.config import get_config
from src.elastic import ElasticService


async def ingest_blogposts(
    config,
    number: int,
    seed: int,
    starting_id: int,
) -> int:
    """Генерирует блогпосты и загружает их в поисковый индекс.

    Блогпосты создаются в памяти (без записи в БД) и вставляются
    в ES батчами по 1000.

    Возвращает количество загруженных блогпостов.
    """
    blogposts = generate_blogposts(
        number=number,
        seed=seed,
        starting_id=starting_id,
    )
    es = ElasticService(config)

    try:
        count = 0
        batch: list = []
        for bp in blogposts:
            batch.append(bp)
            if len(batch) >= 1000:
                await es.blogposts.index_blogposts(batch)
                count += len(batch)
                batch = []

        if batch:
            await es.blogposts.index_blogposts(batch)
            count += len(batch)

        return count
    finally:
        await es.close()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Генерация и загрузка блогпостов в поисковый индекс Elasticsearch"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    parser.add_argument(
        "--number",
        type=int,
        default=1500,
        help="Количество генерируемых блогпостов (по умолчанию: 1500)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Зерно для генератора случайных данных (по умолчанию: 42)",
    )
    parser.add_argument(
        "--starting-id",
        type=int,
        default=1,
        help="Начальный числовой id (по умолчанию: 1)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    count = await ingest_blogposts(
        config,
        number=args.number,
        seed=args.seed,
        starting_id=args.starting_id,
    )
    print(f"Загружено блогпостов в ES: {count}")


if __name__ == "__main__":
    asyncio.run(_main())
