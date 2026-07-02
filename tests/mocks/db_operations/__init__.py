import psycopg

from tests.mocks.db_operations.documents import DocumentDBOperations


class DBOperations:
    """Фасад для операций с тестовой БД."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.documents = DocumentDBOperations(conn)
