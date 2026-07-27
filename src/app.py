from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import Config, get_config
from src.middleware.error import error_middleware
from src.middleware.repository import repository_middleware
from src.routes import setup_routes
from src.elastic import ElasticService, ElasticServiceBase


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
        es = elastic_service if elastic_service is not None else ElasticService(config)
        engine = None
        try:
            engine = create_async_engine(config.db_app_sa_url)
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

    app.middleware("http")(repository_middleware)
    app.middleware("http")(error_middleware)
    setup_routes(app)

    return app
