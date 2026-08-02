from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Query, Request, Response
from pydantic import AfterValidator

from src.elastic import ElasticServiceBase
from src.models import (
    Blogpost,
    BlogpostCreate,
    BlogpostSearchResult,
    BlogpostUpdate,
    ErrorResponse,
    validate_tags_param,
)

router = APIRouter(tags=["blogposts"])

TagsQuery = Annotated[
    str | None,
    AfterValidator(validate_tags_param),
    Query(description="Теги через запятую, до 10"),
]


@router.post(
    "/",
    status_code=201,
    response_model=Blogpost,
    responses={
        409: {
            "description": "Блогпост с таким id уже существует",
            "model": ErrorResponse,
        },
    },
)
async def create_blogpost(request: Request, body: BlogpostCreate) -> Blogpost:
    """Создаёт блогпост в Elasticsearch."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.blogposts.create(body)


@router.get(
    "/search",
    response_model=BlogpostSearchResult,
    responses={
        404: {
            "description": "Блогпосты по заданному запросу не найдены",
            "model": ErrorResponse,
        },
    },
)
async def search_blogposts(
    request: Request,
    q: str = Query(min_length=1, max_length=256, description="Текстовый запрос"),
    min_time: datetime | None = Query(None, description="Нижняя граница updated_at"),
    max_time: datetime | None = Query(None, description="Верхняя граница updated_at"),
    tags: TagsQuery = None,
    p: int = Query(1, ge=1, le=1_000_000, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Элементов на странице"),
) -> BlogpostSearchResult:
    """Полнотекстовый поиск блогпостов с фильтрами и пагинацией."""
    # Валидация tags (длина и количество) — в AfterValidator(TagsQuery),
    # здесь только парсинг строки в список.
    tags_list: list[str] | None = None
    if tags is not None:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.blogposts.search(
        q,
        min_time=min_time if min_time is not None else None,
        max_time=max_time if max_time is not None else None,
        tags=tags_list,
        page=p,
        per_page=per_page,
    )


@router.get(
    "/{blogpost_id}",
    response_model=Blogpost,
    responses={
        404: {
            "description": "Блогпост не найден",
            "model": ErrorResponse,
        },
    },
)
async def get_blogpost(request: Request, blogpost_id: str) -> Blogpost:
    """Возвращает блогпост по id."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.blogposts.get(blogpost_id)


@router.patch(
    "/{blogpost_id}",
    response_model=Blogpost,
    responses={
        404: {
            "description": "Блогпост не найден",
            "model": ErrorResponse,
        },
        409: {
            "description": "Конфликт версий документа",
            "model": ErrorResponse,
        },
    },
)
async def update_blogpost(request: Request, blogpost_id: str, body: BlogpostUpdate) -> Blogpost:
    """Частично обновляет блогпост с optimistic lock."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    return await elastic_service.blogposts.update(blogpost_id, body)


@router.delete(
    "/{blogpost_id}",
    status_code=204,
    response_class=Response,
)
async def delete_blogpost(request: Request, blogpost_id: str):
    """Удаляет блогпост. Возвращает 204 даже если не найден."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    await elastic_service.blogposts.delete(blogpost_id)
