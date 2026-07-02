import asyncio
import sys
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.db.models import Base
from src.models.config import Config

_ALEMBIC_DIR = _project_root / "src" / "db" / "alembic"
_ALEMBIC_INI = _ALEMBIC_DIR / "alembic.ini"


def _make_alembic_cfg(test_config: Config) -> AlembicConfig:
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.attributes["custom_config"] = test_config
    return cfg


def _collect_db_columns(conn: psycopg.Connection) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT table_name, column_name "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public'"
    ).fetchall()

    db_tables: dict[str, set[str]] = {}
    for row in rows:
        db_tables.setdefault(row["table_name"], set()).add(row["column_name"])
    return db_tables


async def test_upgrade_downgrade_each_revision(test_db, test_config: Config) -> None:
    """base → rev1 → base → rev2 → base → ..."""
    alembic_cfg = _make_alembic_cfg(test_config)

    script = ScriptDirectory.from_config(alembic_cfg)
    revisions = [rev.revision for rev in script.walk_revisions()]
    revisions.reverse()

    for rev in revisions:
        await asyncio.to_thread(command.upgrade, alembic_cfg, rev)
        await asyncio.to_thread(command.downgrade, alembic_cfg, "base")


async def test_orm_matches_db_after_migration(
    test_db, test_config: Config
) -> None:
    alembic_cfg = _make_alembic_cfg(test_config)
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    orm_tables: dict[str, set[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        orm_tables[table_name] = {c.name for c in table.columns}

    db_tables = _collect_db_columns(test_db)
    db_tables.pop("alembic_version", None)

    assert orm_tables, "В ORM-метаданных должны быть таблицы"
    for table_name, orm_columns in orm_tables.items():
        assert table_name in db_tables, (
            f"Таблица '{table_name}' отсутствует в БД"
        )
        db_columns = db_tables[table_name]
        missing = orm_columns - db_columns
        assert not missing, (
            f"Колонки {missing} из ORM '{table_name}' не найдены в БД"
        )
        extra = db_columns - orm_columns
        assert not extra, (
            f"Колонки {extra} из БД '{table_name}' не найдены в ORM"
        )
