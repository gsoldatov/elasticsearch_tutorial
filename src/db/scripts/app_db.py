import argparse
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import psycopg
from psycopg import sql

from src.config import Config, get_config


class DBManager:
    """Управление пользователем и БД приложения через подключение
    к дефолтной БД."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._conn = psycopg.connect(config.db_default_url, autocommit=True)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DBManager":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def create_user(self) -> None:
        """Создаёт пользователя приложения, если он ещё не существует."""
        cur = self._conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (self._config.db_app_username,),
        )
        exists = cur.fetchone()
        if not exists:
            self._conn.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
                    sql.Identifier(self._config.db_app_username),
                    sql.Literal(self._config.db_app_password),
                )
            )
            print(f"  ✓ пользователь '{self._config.db_app_username}' создан")
        else:
            print(
                f"  • пользователь '{self._config.db_app_username}' уже существует, пропускаем"
            )

    def create_db(self, database_name: str) -> None:
        """Создаёт БД, если она ещё не существует."""
        cur = self._conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,),
        )
        exists = cur.fetchone()
        if not exists:
            self._conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database_name),
                    sql.Identifier(self._config.db_app_username),
                )
            )
            print(
                f"  ✓ БД '{database_name}' создана"
                f" (владелец: '{self._config.db_app_username}')"
            )
        else:
            print(f"  • БД '{database_name}' уже существует, пропускаем")

    def delete_db(self, database_name: str) -> None:
        """Удаляет БД, предварительно разрывая все подключения к ней."""
        self._conn.execute(
            sql.SQL(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = {} AND pid <> pg_backend_pid()"
            ).format(sql.Literal(database_name))
        )
        self._conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(database_name)
            )
        )

    def delete_user(self) -> None:
        """Удаляет пользователя приложения, если он существует."""
        self._conn.execute(
            sql.SQL("DROP USER IF EXISTS {}").format(
                sql.Identifier(self._config.db_app_username)
            )
        )


def _main() -> None:
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

    with DBManager(config) as db:
        if args.delete_existing:
            print("Удаление БД и пользователя приложения…")
            db.delete_db(config.db_app_database)
            print(f"  ✓ БД '{config.db_app_database}' удалена")
            db.delete_user()
            print(f"  ✓ пользователь '{config.db_app_username}' удалён")

        print("Создание пользователя и БД приложения…")
        db.create_user()
        db.create_db(config.db_app_database)
        print("Готово.")


if __name__ == "__main__":
    _main()
