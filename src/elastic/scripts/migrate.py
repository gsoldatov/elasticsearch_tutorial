import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.config import Config, get_config
from src.elastic import ElasticService


async def migrate(config: Config, current: str, to: str) -> None:
    """Запускает upgrade или downgrade в зависимости от направления."""
    es = ElasticService(config)
    try:
        # Определяем направление по числовым индексам ревизий
        current_idx = es.migrations._resolve_revision(current)
        to_idx = es.migrations._resolve_revision(to)
        if to_idx > current_idx:
            await es.migrations.upgrade(current=current, to=to)
        elif to_idx < current_idx:
            await es.migrations.downgrade(current=current, to=to)
        # иначе: no-op
    finally:
        await es.close()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Запуск миграций Elasticsearch"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    parser.add_argument(
        "--current",
        type=str,
        required=True,
        help="Текущая применённая ревизия ('base' или номер)",
    )
    parser.add_argument(
        "--to",
        type=str,
        required=True,
        help="Целевая ревизия ('head' или номер)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    await migrate(config, current=args.current, to=args.to)
    print(f"  ✓ миграции применены: {args.current} → {args.to}")


if __name__ == "__main__":
    asyncio.run(_main())
