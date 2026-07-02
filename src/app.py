from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import Config, get_config
from src.exceptions import InternalValidationException, NotFoundException
from src.middleware.repository import repository_middleware
from src.routes import setup_routes
from src.services.elastic import ElasticService, ElasticServiceBase


def create_app(
    config: Config | None = None,
    elastic_service: ElasticServiceBase | None = None,
    **kwargs: Any,
) -> FastAPI:
    """Создаёт и настраивает экземпляр FastAPI-приложения.

    Параметры:
        config: Конфигурация приложения. Если не указана — читается из .env.
        elastic_service: Переопределение класса elastic-сервиса.
        **kwargs: Дополнительные параметры, передаваемые в конструктор FastAPI.
    """
    if config is None:
        config = get_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        es = elastic_service if elastic_service is not None else ElasticService()
        engine = None
        try:
            engine = create_async_engine(config.db_app_url)
            app.state.engine = engine
            app.state.elastic_service = es
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            if hasattr(es, "close"):
                await es.close()

    app = FastAPI(lifespan=lifespan, **kwargs)
    app.state.config = config

    @app.exception_handler(NotFoundException)
    async def not_found_handler(
        _request: Request, exc: NotFoundException,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InternalValidationException)
    async def internal_validation_handler(
        _request: Request, _exc: InternalValidationException,
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        _request: Request, _exc: OperationalError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Service unavailable"})

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        _request: Request, _exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.middleware("http")(repository_middleware)
    setup_routes(app)

    return app
