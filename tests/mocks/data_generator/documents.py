from datetime import datetime, timezone

from src.models.document import Document, DocumentCreate


class DocumentDataGenerator:
    """Генератор тестовых Pydantic-моделей документов."""

    @staticmethod
    def document_create(
        text: str = "текст документа для тестов",
        rubrics: list[str] | None = None,
        created_date: str | None = None,
    ) -> DocumentCreate:
        return DocumentCreate(
            text=text,
            rubrics=rubrics if rubrics is not None else ["тест"],
            created_date=(
                created_date
                if created_date is not None
                else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ),
        )

    @staticmethod
    def document(
        id: int = 1,
        text: str = "текст документа для тестов",
        rubrics: list[str] | None = None,
        created_date: datetime | None = None,
    ) -> Document:
        return Document(
            id=id,
            text=text,
            rubrics=rubrics if rubrics is not None else ["тест"],
            created_date=created_date if created_date is not None else datetime.now(timezone.utc),
        )
