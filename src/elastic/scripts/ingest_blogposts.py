import argparse
import asyncio
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from data.blogposts import generate_blogposts
from src.config import get_config
from src.elastic import ElasticService

PROJECT_ROOT = Path(__file__).resolve().parents[3]


async def ingest_blogposts(
    config,
    number: int,
    seed: int,
    starting_id: int,
    *,
    write_file_path: str | None = None,
) -> int:
    """Генерирует блогпосты и загружает их в поисковый индекс.

    Блогпосты создаются в памяти (без записи в БД) и вставляются
    в ES батчами по 1000.

    Если указан write_file_path (относительно корня проекта),
    сгенерированные данные также записываются в JSON-файл.

    Возвращает количество загруженных блогпостов.
    """
    blogposts = generate_blogposts(
        number=number,
        seed=seed,
        starting_id=starting_id,
    )

    if write_file_path is not None:
        target = PROJECT_ROOT / write_file_path
        target.write_text(
            json.dumps(
                [bp.model_dump(mode="json") for bp in blogposts],
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
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
    parser.add_argument(
        "--write-file-path",
        type=str,
        default=None,
        help="Путь относительно корня проекта для сохранения сгенерированных данных в JSON",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    count = await ingest_blogposts(
        config,
        number=args.number,
        seed=args.seed,
        starting_id=args.starting_id,
        write_file_path=args.write_file_path,
    )
    if args.write_file_path:
        print(f"Данные сохранены в {args.write_file_path}")
    print(f"Загружено блогпостов в ES: {count}")


if __name__ == "__main__":
    asyncio.run(_main())
