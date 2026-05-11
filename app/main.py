import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, get_db
from app.observability.correlation import (
    HEADER_NAME,
    get_correlation_id,
    normalize_correlation_id,
    set_correlation_id,
)
from app.observability.errors import problem_response
from app.observability.logging import SERVICE_NAME, configure_logging
from app.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    RESERVATIONS_DATABASE_ERRORS_TOTAL,
)
from app.observability.tracing import configure_tracing
from app.routes import locations, reservations, rooms
from app.seed import run_seed


def create_app(run_seed_on_startup: bool = True) -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    lifespan = build_lifespan() if run_seed_on_startup else None
    app = FastAPI(
        title="Labtrans Reservas - Reservations API",
        version="1.0.0",
        description="Microsservico FastAPI responsavel por locais, salas e CRUD de reservas.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    configure_tracing(app, engine, settings)

    @app.middleware("http")
    async def correlation_and_telemetry_middleware(request: Request, call_next):
        correlation_id = normalize_correlation_id(request.headers.get(HEADER_NAME))
        set_correlation_id(correlation_id)
        method = request.method
        initial_route = request.url.path
        started_at = perf_counter()
        HTTP_REQUESTS_IN_PROGRESS.labels(method, initial_route, SERVICE_NAME).inc()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (perf_counter() - started_at) * 1000
            logging.getLogger("reservations.unhandled").exception(
                "Unhandled request error.",
                extra={
                    "method": method,
                    "path": request.url.path,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "elapsedMs": elapsed_ms,
                },
            )
            response = problem_response(
                request,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Ocorreu um erro inesperado ao processar a requisicao.",
                title="Unexpected error",
            )
        finally:
            HTTP_REQUESTS_IN_PROGRESS.labels(method, initial_route, SERVICE_NAME).dec()

        elapsed_seconds = perf_counter() - started_at
        route = getattr(request.scope.get("route"), "path", request.url.path)
        status_code = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method, route, status_code, SERVICE_NAME).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method, route, status_code, SERVICE_NAME).observe(
            elapsed_seconds
        )
        response.headers[HEADER_NAME] = correlation_id

        logging.getLogger("reservations.request").info(
            "HTTP request completed.",
            extra={
                "method": method,
                "path": request.url.path,
                "route": route,
                "statusCode": response.status_code,
                "elapsedMs": elapsed_seconds * 1000,
                "userId": getattr(request.state, "user_id", None),
                "userEmail": getattr(request.state, "user_email", None),
            },
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return problem_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            "Dados invalidos.",
            title="Validation error",
            extra={"details": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        extra = None
        detail = str(exc.detail)
        if isinstance(exc.detail, dict):
            detail = str(exc.detail.get("message", detail))
            extra = {
                key: value for key, value in exc.detail.items() if key not in {"message", "detail"}
            }
        return problem_response(
            request,
            exc.status_code,
            detail,
            headers=exc.headers,
            extra=extra,
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "correlationId": get_correlation_id(),
        }

    @app.get("/health/live", tags=["health"])
    def live_health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "correlationId": get_correlation_id(),
        }

    @app.get("/health/ready", tags=["health"])
    def ready_health():
        checks = {
            "configuration": (
                "ok"
                if all(
                    [
                        settings.database_url,
                        settings.jwt_secret,
                        settings.jwt_issuer,
                        settings.jwt_audience,
                    ]
                )
                else "error"
            )
        }

        try:
            db = next(get_db())
            try:
                db.execute(text("SELECT 1"))
                checks["database"] = "ok"
            finally:
                db.close()
        except Exception:
            RESERVATIONS_DATABASE_ERRORS_TOTAL.inc()
            checks["database"] = "error"

        ready = all(value == "ok" for value in checks.values())
        body = {
            "status": "ready" if ready else "not_ready",
            "service": SERVICE_NAME,
            "checks": checks,
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "correlationId": get_correlation_id(),
        }
        return Response(
            content=json.dumps(body),
            media_type="application/json",
            status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(locations.router)
    app.include_router(rooms.router)
    app.include_router(reservations.router)
    return app


def build_lifespan():
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        run_seed()
        yield

    return lifespan


app = create_app()
