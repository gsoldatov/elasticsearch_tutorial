import argparse
import asyncio
import csv
import sys
from itertools import batched
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import get_config
from src.db.models import Document
from src.models import DocumentCreate


async def ingest_data(config, csv_path: Path) -> int:
    """Читает CSV, валидирует строки и вставляет их в БД.

    Возвращает количество загруженных документов.
    """
    engine = create_async_engine(config.db_app_url)
    async_session = async_sessionmaker(engine)

    # Чтение и валидация CSV
    documents: list[dict] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc = DocumentCreate.model_validate(row)
            documents.append(doc.model_dump())

    if not documents:
        print("CSV-файл пуст, нечего загружать.")
        return 0

    # Массовая вставка в БД
    async with async_session() as session:
        for batch in batched(documents, 1000):
            async with session.begin():
                stmt = insert(Document).values(list(batch))
                await session.execute(stmt)

    return len(documents)


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Загрузка документов из CSV-файла в БД приложения"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        default="data/posts.csv",
        help="Путь к CSV-файлу с данными (по умолчанию — data/posts.csv)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)
    csv_path = Path(args.csv_file)
    if not csv_path.is_absolute():
        csv_path = Path.cwd() / csv_path

    count = await ingest_data(config, csv_path)
    print(f"Загружено документов: {count}")


if __name__ == "__main__":
    asyncio.run(_main())
