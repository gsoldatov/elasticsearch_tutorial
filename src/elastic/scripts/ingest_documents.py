import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import get_config
from src.db.models import Documents
from src.elastic import ElasticService
from src.models.document import Document


async def ingest_documents(config) -> tuple[int, int]:
    """Читает документы из БД и загружает их в поисковый индекс.

    Использует серверный курсор для потокового чтения, чтобы не загружать
    все строки в память одновременно.

    Возвращает (количество загруженных документов, общее количество).
    """
    engine = create_async_engine(config.db_app_sa_url)
    async_session = async_sessionmaker(engine)
    es = ElasticService(config)

    try:
        async with async_session() as session:
            total = await session.scalar(
                select(func.count()).select_from(Documents)
            )
            if total is None:
                total = 0
            width = len(str(total)) if total > 0 else 1

            stream = await session.stream_scalars(select(Documents))

            count = 0
            batch: list[Document] = []
            i = 0
            async for row in stream:
                batch.append(Document.model_validate(row))
                i += 1
                if len(batch) >= 1000 or i == total:
                    await es.documents.index_documents(batch)
                    count += len(batch)
                    print(
                        f"\rЗагружено документов: {count:>{width}d} / {total}",
                        end="",
                        flush=True,
                    )
                    batch = []
            print()

        return count, total
    finally:
        await es.close()
        await engine.dispose()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Загрузка документов из БД в поисковый индекс Elasticsearch"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    await ingest_documents(config)


if __name__ == "__main__":
    asyncio.run(_main())
