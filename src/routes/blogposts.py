from typing import cast

from fastapi import APIRouter, Request, Response

from src.elastic import ElasticServiceBase
from src.models import Blogpost, BlogpostCreate, BlogpostUpdate, ErrorResponse

router = APIRouter(tags=["blogposts"])


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
