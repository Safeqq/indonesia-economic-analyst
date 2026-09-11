from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.api.routes import router
from backend.models.schemas import ErrorResponse
from backend.services.exceptions import DataIntegrityError, ResourceNotFoundError
from pipelines.utils.database import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
EngineFactory = Callable[[], Engine]


def create_database_engine() -> Engine:
    load_dotenv(PROJECT_ROOT / ".env")
    return get_engine()


def create_app(
    *,
    engine: Engine | None = None,
    engine_factory: EngineFactory = create_database_engine,
) -> FastAPI:
    owns_engine = engine is None

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.engine = engine if engine is not None else engine_factory()
        try:
            yield
        finally:
            if owns_engine:
                application.state.engine.dispose()

    application = FastAPI(
        title="Indonesia Economic Intelligence API",
        version="0.2.0",
        description=(
            "API read-only untuk indikator ekonomi, analytical marts, "
            "quality checks, dan estimasi model."
        ),
        lifespan=lifespan,
    )
    application.include_router(router)

    @application.exception_handler(ResourceNotFoundError)
    async def resource_not_found(
        _request: Request, error: ResourceNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(detail=str(error)).model_dump(),
        )

    @application.exception_handler(DataIntegrityError)
    async def invalid_stored_data(
        _request: Request, error: DataIntegrityError
    ) -> JSONResponse:
        LOGGER.error("API data integrity error: %s", error)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail="Data tersimpan tidak memenuhi kontrak API"
            ).model_dump(),
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_unavailable(
        _request: Request, error: SQLAlchemyError
    ) -> JSONResponse:
        LOGGER.error("API database error: %s", error.__class__.__name__)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                detail="Layanan data sementara tidak tersedia"
            ).model_dump(),
        )

    return application


app = create_app()
