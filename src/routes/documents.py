from typing import cast

from fastapi import APIRouter, Request, Response

from src.db.repository import Repository
from src.elastic import ElasticServiceBase

router = APIRouter(tags=["documents"])


@router.delete(
    "/documents/{doc_id}",
    status_code=204,
    response_class=Response,
)
async def delete_document(request: Request, doc_id: int) -> None:
    """Удаляет документ по id из БД и поискового индекса."""
    elastic_service = cast(ElasticServiceBase, request.app.state.elastic_service)
    repository = cast(Repository, request.state.repository)

    await repository.document.delete_by_id(doc_id)
    # TODO: если удаление из ES упадёт после успешного удаления из БД,
    #       документ останется в поисковом индексе, но исчезнет из Postgres.
    #       Нужно решить порядок удаления (ES → DB) или добавить компенсацию.
    await elastic_service.delete(doc_id)
