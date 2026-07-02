import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from psycopg import sql
from psycopg.rows import dict_row

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.app import create_app
from src.config import get_config
from src.models.config import Config
from tests.mocks.data_generator import DataGenerator
from tests.mocks.db_operations import DBOperations
from tests.mocks.elastic_mock import ElasticServiceMock


# ── Module scope ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_db_name() -> str:
    return f"test_{uuid4().hex}"


@pytest.fixture(scope="module")
def test_config(test_db_name: str) -> Config:
    config = get_config(".env.example")
    config.db_app_database = test_db_name
    return config


@pytest.fixture(scope="module")
def test_db(test_config: Config):
    """Создаёт тестовую БД и возвращает autocommit-соединение с dict_row."""

    # Создать БД через дефолтное подключение
    admin_conn = psycopg.connect(
        host=test_config.db_host,
        port=test_config.db_port,
        user=test_config.db_default_username,
        password=test_config.db_default_password,
        dbname=test_config.db_default_database,
        autocommit=True,
    )
    try:
        admin_conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(test_config.db_app_database),
                sql.Identifier(test_config.db_app_username),
            )
        )
    finally:
        admin_conn.close()

    # Подключиться к тестовой БД
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

    test_conn.close()

    # Удалить тестовую БД
    admin_conn = psycopg.connect(
        host=test_config.db_host,
        port=test_config.db_port,
        user=test_config.db_default_username,
        password=test_config.db_default_password,
        dbname=test_config.db_default_database,
        autocommit=True,
    )
    try:
        admin_conn.execute(
            sql.SQL(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = {} AND pid <> pg_backend_pid()"
            ).format(sql.Literal(test_config.db_app_database))
        )
        admin_conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(test_config.db_app_database)
            )
        )
    finally:
        admin_conn.close()


@pytest.fixture(scope="module")
def test_db_migrations(test_db, test_config: Config):
    """Применяет миграции к тестовой БД."""
    alembic_dir = _project_root / "src" / "db" / "alembic"
    alembic_ini = alembic_dir / "alembic.ini"

    alembic_cfg = AlembicConfig(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.attributes["custom_config"] = test_config

    command.upgrade(alembic_cfg, "head")
    yield


# ── Function scope ────────────────────────────────────────────────────────


@pytest.fixture
def clean_db(test_db):
    """Очищает таблицы после каждого теста."""
    yield test_db
    test_db.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")


@pytest.fixture
def elastic_mock() -> ElasticServiceMock:
    return ElasticServiceMock()


@pytest.fixture
async def test_app(test_db_migrations, test_config: Config, elastic_mock: ElasticServiceMock):
    app = create_app(test_config, elastic_service=elastic_mock)
    yield app
    if hasattr(app.state, "engine"):
        await app.state.engine.dispose()


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
