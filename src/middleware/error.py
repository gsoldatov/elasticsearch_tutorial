from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from elasticsearch import ConnectionError

from src.exceptions import InternalValidationException, NotFoundException, UpdateConflict
from src.models import ErrorResponse


async def error_middleware(request: Request, call_next):
    """
    Перехватывает необработанные исключения и возвращает HTTP-ответы с ошибками.
    """
    try:
        return await call_next(request)
    except NotFoundException as exc:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )
    except InternalValidationException:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="Внутренняя ошибка сервера").model_dump(),
        )
    except OperationalError:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(detail="Сервис недоступен").model_dump(),
        )
    except ConnectionError:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(detail="Сервис недоступен").model_dump(),
        )
    except UpdateConflict as exc:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="Внутренняя ошибка сервера").model_dump(),
        )
