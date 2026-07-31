from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

from src.models.common import AnyOf

_Tag = Annotated[str, Field(min_length=1, max_length=64)]
_Title = Annotated[str, Field(min_length=1, max_length=256)]
_Text = Annotated[str, Field(min_length=0, max_length=8192)]
_Tags = Annotated[list[_Tag], Field(min_length=0, max_length=100)]


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
