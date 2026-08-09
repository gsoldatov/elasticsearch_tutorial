import argparse
import asyncio
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from data.sales import generate_sales
from src.config import get_config
from src.elastic import ElasticService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_GEN_BATCH_SIZE = 1000
_SEED_STEP = 1000


async def ingest_sales(
    config,
    number: int,
    seed: int,
    *,
    write_file_path: str | None = None,
) -> int:
    """Генерирует продажи и загружает их в поисковый индекс.

    Продажи создаются в памяти и вставляются в ES батчами по 1000.

    Если указан write_file_path (относительно корня проекта),
    сгенерированные данные также записываются в JSON-файл.

    Возвращает количество загруженных продаж.
    """
    # Генерация батчами с прогрессом
    sales = []
    width = len(str(number))
    for offset in range(0, number, _GEN_BATCH_SIZE):
        batch_n = min(_GEN_BATCH_SIZE, number - offset)
        batch_seed = seed + (offset // _GEN_BATCH_SIZE) * _SEED_STEP
        batch = generate_sales(number=batch_n, seed=batch_seed)
        sales.extend(batch)
        print(
            f"\rСгенерировано продаж: {len(sales):>{width}d} / {number}",
            end="",
            flush=True,
        )
    print()

    if write_file_path is not None:
        target = PROJECT_ROOT / write_file_path
        target.write_text(
            json.dumps(
                [s.to_dict() for s in sales],
                ensure_ascii=False,
                indent=4,
                default=str,
            ),
            encoding="utf-8",
        )
    es = ElasticService(config)

    try:
        count = 0
        batch: list = []
        for i, sale in enumerate(sales, start=1):
            batch.append(sale)
            if len(batch) >= 1000 or i == number:
                await es.sales.index_sales(batch)
                count += len(batch)
                print(
                    f"\rЗагружено продаж: {count:>{width}d} / {number}",
                    end="",
                    flush=True,
                )
                batch = []
        print()

        return count
    finally:
        await es.close()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Генерация и загрузка продаж в поисковый индекс Elasticsearch"
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
        default=10000,
        help="Количество генерируемых продаж (по умолчанию: 10000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Зерно для генератора случайных данных (по умолчанию: 42)",
    )
    parser.add_argument(
        "--write-file-path",
        type=str,
        default=None,
        help="Путь относительно корня проекта для сохранения сгенерированных данных в JSON",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    count = await ingest_sales(
        config,
        number=args.number,
        seed=args.seed,
        write_file_path=args.write_file_path,
    )
    if args.write_file_path:
        print(f"Данные сохранены в {args.write_file_path}")


if __name__ == "__main__":
    asyncio.run(_main())
