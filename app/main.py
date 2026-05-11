from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import locations, reservations, rooms
from app.seed import run_seed


def create_app(run_seed_on_startup: bool = True) -> FastAPI:
    settings = get_settings()
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

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder({"message": "Dados invalidos.", "details": exc.errors()}),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        content = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return JSONResponse(
            status_code=exc.status_code, content=jsonable_encoder(content), headers=exc.headers
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
