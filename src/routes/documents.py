from typing import cast

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from src.db.repository import Repository
from src.elastic import ElasticServiceBase
from src.exceptions import NotFoundException
from src.models import ErrorResponse

router = APIRouter(tags=["documents"])


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

    await elastic_service.delete(doc_id)
    try:
        await repository.document.delete_by_id(doc_id)
    except NotFoundException as e:
        return JSONResponse(
            status_code=404, content=ErrorResponse(detail=str(e)).model_dump()
        )
