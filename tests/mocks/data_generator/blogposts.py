from datetime import datetime, timezone

from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostUpdate


class BlogpostDataGenerator:
    """Генератор тестовых Pydantic-моделей блогпостов."""

    @staticmethod
    def blogpost_create(
        title: str = "тестовый заголовок",
        text: str = "тестовый текст блогпоста",
        tags: list[str] | None = None,
        id: str | None = None,
        updated_at: datetime | None = None,
    ) -> BlogpostCreate:
        return BlogpostCreate(
            title=title,
            text=text,
            tags=tags if tags is not None else ["тест"],
            id=id,
            updated_at=updated_at,
        )

    @staticmethod
    def blogpost(
        id: str = "test-id-1",
        title: str = "тестовый заголовок",
        text: str = "тестовый текст блогпоста",
        tags: list[str] | None = None,
        updated_at: datetime | None = None,
    ) -> Blogpost:
        return Blogpost(
            id=id,
            title=title,
            text=text,
            tags=tags if tags is not None else ["тест"],
            updated_at=updated_at if updated_at is not None else datetime.now(timezone.utc),
        )

    @staticmethod
    def blogpost_update(
        title: str | None = "обновлённый заголовок",
        text: str | None = None,
        tags: list[str] | None = None,
        updated_at: datetime | None = None,
    ) -> BlogpostUpdate:
        return BlogpostUpdate(
            title=title,
            text=text,
            tags=tags,
            updated_at=updated_at,
        )
