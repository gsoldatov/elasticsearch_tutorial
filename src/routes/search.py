from typing import cast

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.db.repository import Repository
from src.models import Document, ErrorResponse
from src.elastic import ElasticServiceBase
from src.exceptions import NotFoundException

router = APIRouter(tags=["search"])


@router.get(
    "/search",
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
) -> list[Document] | JSONResponse:
    """
    Поиск документов по тексту.
    Возвращает до 20 документов, упорядоченных по дате создания.
    """
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    repository = cast(Repository, request.state.repository)

    try:
        ids = await elastic_service.search(q)
        return await repository.document.get_by_ids(ids, limit=20)
    except NotFoundException as e:
        return JSONResponse(
            status_code=404, content=ErrorResponse(detail=str(e)).model_dump()
        )
