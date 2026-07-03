import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.config import get_config
from src.elastic import ElasticService


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Создание поискового индекса Elasticsearch"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    es = ElasticService(config)
    try:
        await es.create_index()
        print(f"  ✓ индекс '{config.es_documents_index_name}' создан")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(_main())
