import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import get_config
from src.db.models import Document
from src.elastic import ElasticService


async def ingest_es_data(config) -> int:
    """Читает документы из БД и загружает их в поисковый индекс.

    Использует серверный курсор для потокового чтения, чтобы не загружать
    все строки в память одновременно.

    Возвращает количество загруженных документов.
    """
    engine = create_async_engine(config.db_app_url)
    async_session = async_sessionmaker(engine)
    es = ElasticService(config)

    try:
        await es.create_index()

        async with async_session() as session:
            stream = await session.stream(select(Document.id, Document.text))

            count = 0
            batch: list[dict] = []
            async for row in stream:
                batch.append({"id": row[0], "text": row[1]})
                if len(batch) >= 1000:
                    await es.index_documents(batch)
                    count += len(batch)
                    batch = []

            if batch:
                await es.index_documents(batch)
                count += len(batch)

        return count
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
    count = await ingest_es_data(config)
    print(f"Загружено документов в ES: {count}")


if __name__ == "__main__":
    asyncio.run(_main())
