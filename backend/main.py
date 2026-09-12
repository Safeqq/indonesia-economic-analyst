from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.api.routes import router
from backend.models.schemas import ErrorResponse
from backend.services.exceptions import DataIntegrityError, ResourceNotFoundError
from pipelines.utils.database import get_engine
from pipelines.utils.structured_logging import configure_logging, log_event

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
EngineFactory = Callable[[], Engine]


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as error:
            log_event(
                LOGGER,
                logging.ERROR,
                "api_request_failed",
                "Request API gagal sebelum respons selesai",
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
                error_type=error.__class__.__name__,
            )
            raise
        log_event(
            LOGGER,
            logging.INFO,
            "api_request_completed",
            "Request API selesai",
            request_id=request_id,
            method=scope.get("method"),
            path=scope.get("path"),
            status_code=status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )


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
        version="0.3.0",
        description=(
            "API read-only untuk indikator ekonomi, analytical marts, "
            "quality checks, dan estimasi model."
        ),
        lifespan=lifespan,
    )
    application.include_router(router)
    application.add_middleware(RequestLoggingMiddleware)

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
        log_event(
            LOGGER,
            logging.ERROR,
            "api_data_integrity_error",
            "Data tersimpan tidak memenuhi kontrak API",
            error_type=error.__class__.__name__,
        )
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
        log_event(
            LOGGER,
            logging.ERROR,
            "api_database_error",
            "Database API tidak tersedia",
            error_type=error.__class__.__name__,
        )
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                detail="Layanan data sementara tidak tersedia"
            ).model_dump(),
        )

    return application


configure_logging()
app = create_app()
