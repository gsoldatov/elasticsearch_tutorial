import psycopg

from src.models.document import Document, DocumentCreate


class DocumentDBOperations:
    """Сырой SQL для таблицы documents (синхронный, autocommit)."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def insert(self, data: DocumentCreate) -> Document:
        row = self._conn.execute(
            "INSERT INTO documents (text, rubrics, created_date) "
            "VALUES (%(text)s, %(rubrics)s, %(created_date)s) "
            "RETURNING id, text, rubrics, created_date",
            {
                "text": data.text,
                "rubrics": data.rubrics,
                "created_date": data.created_date,
            },
        ).fetchone()
        return Document.model_validate(dict(row))

    def by_id(self, doc_id: int) -> Document | None:
        row = self._conn.execute(
            "SELECT id, text, rubrics, created_date FROM documents WHERE id = %(id)s",
            {"id": doc_id},
        ).fetchone()
        if row is None:
            return None
        return Document.model_validate(dict(row))

    def list_all(self, limit: int = 100) -> list[Document]:
        rows = self._conn.execute(
            "SELECT id, text, rubrics, created_date FROM documents "
            "ORDER BY created_date DESC "
            "LIMIT %(limit)s",
            {"limit": limit},
        ).fetchall()
        return [Document.model_validate(dict(r)) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return row[0]
