import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from elasticsearch import Elasticsearch
from psycopg.rows import dict_row

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.app import create_app
from src.config import get_config
from src.db.scripts.app_db import DBManager
from src.models.config import Config
from tests.mocks.data_generator import DataGenerator
from tests.mocks.db_operations import DBOperations
from tests.mocks.elastic_mock import ElasticServiceMock
from tests.mocks.elastic_operations import ElasticOperations


# ── Module scope ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_uuid() -> str:
    return uuid4().hex


@pytest.fixture(scope="module")
def test_config(test_uuid: str) -> Config:
    config = get_config(".env.example")
    config.db_app_database = f"{config.db_app_database}_test_{test_uuid}"
    config.es_documents_index_name = f"{config.es_documents_index_name}_test_{test_uuid}"
    return config


@pytest.fixture(scope="module")
def test_db(test_config: Config):
    """Создаёт тестовую БД и возвращает autocommit-соединение с dict_row."""
    with DBManager(test_config) as db_manager:
        db_manager.create_user()
        db_manager.create_db(test_config.db_app_database)

        test_conn = None
        try:
            test_conn = psycopg.connect(
                host=test_config.db_host,
                port=test_config.db_port,
                user=test_config.db_app_username,
                password=test_config.db_app_password,
                dbname=test_config.db_app_database,
                autocommit=True,
                row_factory=dict_row,
            )

            yield test_conn
        finally:
            if test_conn is not None:
                test_conn.close()
            db_manager.delete_db(test_config.db_app_database)


@pytest.fixture(scope="module")
def test_db_migrations(test_db: psycopg.Connection, test_config: Config):
    """Применяет миграции к тестовой БД."""
    alembic_dir = _project_root / "src" / "db" / "alembic"
    alembic_ini = alembic_dir / "alembic.ini"

    alembic_cfg = AlembicConfig(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.attributes["custom_config"] = test_config

    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(scope="module")
def test_elastic_index(test_config: Config):
    """Создаёт тестовый ES-индекс и возвращает клиент с именем индекса."""
    client = Elasticsearch(
        test_config.es_url,
        basic_auth=("elastic", test_config.es_superuser_password),
    )
    index_name = test_config.es_documents_index_name
    ops = ElasticOperations(client, index_name)
    try:
        ops.create_index()
        yield client, index_name
    finally:
        ops.delete_index()
        client.close()


# ── Function scope ────────────────────────────────────────────────────────


@pytest.fixture
def clean_db(test_db: psycopg.Connection):
    """Очищает таблицы после каждого теста."""
    yield test_db
    test_db.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")


@pytest.fixture
def elastic_mock() -> ElasticServiceMock:
    return ElasticServiceMock()


@pytest.fixture
def elastic_operations(test_elastic_index) -> ElasticOperations:
    client, index_name = test_elastic_index
    return ElasticOperations(client, index_name)


@pytest.fixture
async def real_elastic_service(test_config: Config, test_elastic_index):
    """
    ElasticService, использующий индекс из test_elastic_index.
    
    Очищает индекс после теста.
    """
    from src.elastic import ElasticService

    client, index_name = test_elastic_index
    es = ElasticService(test_config, refresh=True)
    try:
        yield es
    finally:
        try:
            ElasticOperations(client, index_name).delete_all()
        except Exception:
            pass
        await es.close()


@pytest.fixture
async def test_app(test_db_migrations, test_config: Config, elastic_mock: ElasticServiceMock):
    app = create_app(test_config, elastic_service=elastic_mock)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def test_client(test_app):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def data_generator() -> DataGenerator:
    return DataGenerator()


@pytest.fixture
def db_operations(clean_db) -> DBOperations:
    return DBOperations(clean_db)
