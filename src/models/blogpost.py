from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

from src.models.common import AnyOf

# Константы для валидации тегов
_TAG_MIN_LENGTH = 1
_TAG_MAX_LENGTH = 64

_Tag = Annotated[str, Field(min_length=_TAG_MIN_LENGTH, max_length=_TAG_MAX_LENGTH)]
_Title = Annotated[str, Field(min_length=1, max_length=256)]
_Text = Annotated[str, Field(min_length=0, max_length=8192)]
_Tags = Annotated[list[_Tag], Field(min_length=0, max_length=100)]

# Отдельное ограничение для поиска: не более 10 тегов в query-параметре
_SEARCH_TAGS_MAX_COUNT = 10


def validate_tags_param(v: str | None) -> str | None:
    """Валидирует строку тегов из query-параметра: разбивает по запятой
    и проверяет каждый тег.

    Ограничения:
    - не более 10 тегов (query-специфичное ограничение);
    - каждый тег от 1 до 64 символов (совпадает с полем tags модели Blogpost).
    """
    if v is None:
        return v
    tags_list = [t.strip() for t in v.split(",")]
    if len(tags_list) > _SEARCH_TAGS_MAX_COUNT:
        raise ValueError(
            f"Значение параметра tags должно содержать не более "
            f"{_SEARCH_TAGS_MAX_COUNT} элементов"
        )
    for tag in tags_list:
        if len(tag) < _TAG_MIN_LENGTH or len(tag) > _TAG_MAX_LENGTH:
            raise ValueError(
                f"Длина каждого тега должна быть от {_TAG_MIN_LENGTH} "
                f"до {_TAG_MAX_LENGTH} символов"
            )
    return v


def _coerce_iso_datetime(v: Any) -> Any:
    """Преобразует строку ISO в datetime для strict-режима."""
    if isinstance(v, str):
        return datetime.fromisoformat(v)
    return v


_UpdatedAt = Annotated[datetime, BeforeValidator(_coerce_iso_datetime)]


class BlogpostCreate(BaseModel):
    """Модель для создания поста."""

    model_config = ConfigDict(strict=True)

    id: str | None = None
    title: _Title
    text: _Text
    tags: _Tags
    updated_at: _UpdatedAt | None = None


class BlogpostUpdate(BaseModel, AnyOf):
    """Модель для частичного обновления поста."""

    model_config = ConfigDict(strict=True)

    title: _Title | None = None
    text: _Text | None = None
    tags: _Tags | None = None
    updated_at: _UpdatedAt | None = None


class Blogpost(BaseModel):
    """Полное представление поста."""

    model_config = ConfigDict(strict=True)

    id: str
    title: _Title
    text: _Text
    tags: _Tags
    updated_at: _UpdatedAt


class BlogpostSearchResult(BaseModel):
    """Результат поиска блогпостов с пагинацией."""

    model_config = ConfigDict(strict=True)

    items: list[Blogpost]
    total: int
