import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg.rows import DictRow, dict_row

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.app import create_app
from src.config import get_config
from src.db.scripts.app_db import DBManager
from src.elastic import ElasticService
from src.models.config import Config
from tests.mocks.data_generator import DataGenerator
from tests.mocks.db_operations import DBOperations
from tests.mocks.elastic_mock import ElasticServiceMock
from tests.mocks.elastic_operations import ElasticOperations


# ── Уровень модуля ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_uuid() -> str:
    return uuid4().hex


@pytest.fixture(scope="module")
def test_config(test_uuid: str) -> Config:
    config = get_config(".env.example")
    config.db_app_database = f"{config.db_app_database}_test_{test_uuid}"
    config.es_documents_index_name = f"{config.es_documents_index_name}_test_{test_uuid}"
    config.es_blogposts_index_name = f"{config.es_blogposts_index_name}_test_{test_uuid}"
    return config


@pytest.fixture(scope="module")
def test_db(test_config: Config) -> Generator[psycopg.Connection[DictRow], None, None]:
    """Создаёт тестовую БД и возвращает autocommit-соединение с dict_row."""
    with DBManager(test_config) as db_manager:
        db_manager.create_user()
        db_manager.create_db(test_config.db_app_database)

        test_conn: psycopg.Connection[DictRow] | None = None
        try:
            test_conn = psycopg.Connection[DictRow].connect(
                test_config.db_app_url,
                autocommit=True,
                row_factory=dict_row,
            )

            yield test_conn
        finally:
            if test_conn is not None:
                test_conn.close()
            db_manager.delete_db(test_config.db_app_database)


@pytest.fixture(scope="module")
def test_db_migrations(test_db: psycopg.Connection, test_config: Config) -> None:
    """Применяет миграции к тестовой БД."""
    alembic_dir = _project_root / "src" / "db" / "alembic"
    alembic_ini = alembic_dir / "alembic.ini"

    alembic_cfg = AlembicConfig(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.attributes["custom_config"] = test_config

    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="module")
async def test_elastic_migrations(
    test_config: Config
) -> AsyncGenerator[None, None]:
    """Применяет ES-миграции к тестовым индексам."""
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="head")
        yield
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── Уровень функции ───────────────────────────────────────────────────────


@pytest.fixture
def clean_db(test_db: psycopg.Connection) -> Generator[psycopg.Connection, None, None]:
    """Очищает таблицы после каждого теста."""
    yield test_db
    test_db.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")


@pytest.fixture
def elastic_service_mock() -> ElasticServiceMock:
    return ElasticServiceMock()


@pytest.fixture
def elastic_operations(test_config: Config, test_elastic_migrations: None) -> Generator[ElasticOperations, None, None]:
    ops = ElasticOperations(test_config)
    try:
        yield ops
    finally:
        ops.close()


@pytest.fixture
async def elastic_service(
    test_config: Config,
    elastic_operations: ElasticOperations,
) -> AsyncGenerator[ElasticService, None]:
    """ElasticService с очисткой индексов после каждого теста."""
    es = ElasticService(test_config, refresh=True)
    try:
        yield es
    finally:
        try:
            elastic_operations.truncate_indices()
        except Exception:
            pass
        await es.close()


@pytest.fixture
async def test_app(
    test_db_migrations: None,
    test_config: Config,
    elastic_service_mock: ElasticServiceMock,
) -> AsyncGenerator[FastAPI, None]:
    app = create_app(test_config, elastic_service=elastic_service_mock)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def data_generator() -> DataGenerator:
    return DataGenerator()


@pytest.fixture
def db_operations(clean_db: psycopg.Connection) -> DBOperations:
    return DBOperations(clean_db)
