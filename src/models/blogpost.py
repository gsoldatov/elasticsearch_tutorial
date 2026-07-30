from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from src.models.common import AnyOf

_Tag = Annotated[str, Field(min_length=1, max_length=64)]
_Title = Annotated[str, Field(min_length=1, max_length=256)]
_Text = Annotated[str, Field(min_length=0, max_length=8192)]
_Tags = Annotated[list[_Tag], Field(min_length=0, max_length=100)]


class BlogpostCreate(BaseModel):
    """Модель для создания поста."""

    model_config = ConfigDict(strict=True)

    title: _Title
    text: _Text
    tags: _Tags


class BlogpostUpdate(BaseModel, AnyOf):
    """Модель для частичного обновления поста."""

    model_config = ConfigDict(strict=True)

    title: _Title | None = None
    text: _Text | None = None
    tags: _Tags | None = None


class Blogpost(BaseModel):
    """Полное представление поста."""

    model_config = ConfigDict(strict=True)

    id: str
    title: _Title
    text: _Text
    tags: _Tags
    updated_at: datetime
