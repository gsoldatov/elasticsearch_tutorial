from typing import cast

from fastapi import APIRouter, Query, Request, Response

from src.db.repository import Repository
from src.elastic import ElasticServiceBase
from src.models import Document, ErrorResponse

router = APIRouter(tags=["documents"])


@router.get(
    "/documents/search",
    response_model=list[Document],
    responses={
        404: {
            "description": "Документы по заданному запросу не найдены",
            "model": ErrorResponse,
        },
    },
)
async def search(
    request: Request,
    q: str = Query(min_length=1, description="Текстовый запрос"),
) -> list[Document]:
    """
    Поиск документов по тексту.
    Возвращает до 20 документов, упорядоченных по дате создания.
    """
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    repository = cast(Repository, request.state.repository)

    ids = await elastic_service.documents.search(q)
    return await repository.document.get_by_ids(ids, limit=20)


@router.delete(
    "/documents/{doc_id}",
    status_code=204,
    response_class=Response,
    responses={
        404: {
            "description": "Документ не найден",
            "model": ErrorResponse,
        },
    },
)
async def delete_document(request: Request, doc_id: int):
    """Удаляет документ по id из поискового индекса и БД."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    repository = cast(Repository, request.state.repository)

    await elastic_service.documents.delete(doc_id)
    await repository.document.delete_by_id(doc_id)
