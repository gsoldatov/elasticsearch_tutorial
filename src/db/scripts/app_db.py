import argparse
import asyncio
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import psycopg
from psycopg import sql

from src.config import Config, get_config


async def delete_app_db(config: Config) -> None:
    """Удаляет БД приложения, предварительно разрывая все подключения к ней."""
    conn = await psycopg.AsyncConnection.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_default_username,
        password=config.db_default_password,
        dbname=config.db_default_database,
        autocommit=True,
    )
    try:
        # Разрываем все активные подключения к БД приложения, кроме текущего
        await conn.execute(
            sql.SQL(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = {} AND pid <> pg_backend_pid()"
            ).format(sql.Literal(config.db_app_database))
        )
        await conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(config.db_app_database)
            )
        )
    finally:
        await conn.close()


async def delete_app_user(config: Config) -> None:
    """Удаляет пользователя приложения, если он существует."""
    conn = await psycopg.AsyncConnection.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_default_username,
        password=config.db_default_password,
        dbname=config.db_default_database,
        autocommit=True,
    )
    try:
        await conn.execute(
            sql.SQL("DROP USER IF EXISTS {}").format(
                sql.Identifier(config.db_app_username)
            )
        )
    finally:
        await conn.close()


async def create_user(config: Config) -> None:
    """Создаёт пользователя приложения, если он ещё не существует."""
    conn = await psycopg.AsyncConnection.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_default_username,
        password=config.db_default_password,
        dbname=config.db_default_database,
        autocommit=True,
    )
    try:
        cur = await conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (config.db_app_username,),
        )
        exists = await cur.fetchone()
        if not exists:
            await conn.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
                    sql.Identifier(config.db_app_username),
                    sql.Literal(config.db_app_password),
                )
            )
            print(f"  ✓ пользователь '{config.db_app_username}' создан")
        else:
            print(f"  • пользователь '{config.db_app_username}' уже существует, пропускаем")
    finally:
        await conn.close()


async def create_db(config: Config) -> None:
    """Создаёт БД приложения, если она ещё не существует."""
    conn = await psycopg.AsyncConnection.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_default_username,
        password=config.db_default_password,
        dbname=config.db_default_database,
        autocommit=True,
    )
    try:
        cur = await conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.db_app_database,),
        )
        exists = await cur.fetchone()
        if not exists:
            await conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(config.db_app_database),
                    sql.Identifier(config.db_app_username),
                )
            )
            print(f"  ✓ БД '{config.db_app_database}' создана (владелец: '{config.db_app_username}')")
        else:
            print(f"  • БД '{config.db_app_database}' уже существует, пропускаем")
    finally:
        await conn.close()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Скрипт для создания пользователя и БД приложения"
    )
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        default=False,
        help="Предварительно удалить существующие БД и пользователя приложения",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file)

    if args.delete_existing:
        print("Удаление БД и пользователя приложения…")
        await delete_app_db(config)
        print(f"  ✓ БД '{config.db_app_database}' удалена")
        await delete_app_user(config)
        print(f"  ✓ пользователь '{config.db_app_username}' удалён")

    print("Создание пользователя и БД приложения…")
    await create_user(config)
    await create_db(config)
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(_main())
