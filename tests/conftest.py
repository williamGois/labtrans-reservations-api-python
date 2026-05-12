from collections.abc import Generator
from datetime import datetime, timedelta, UTC
import os
import secrets

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

TEST_SECRET = os.environ.get("JWT_SECRET") or secrets.token_urlsafe(48)
os.environ.setdefault("JWT_SECRET", TEST_SECRET)
os.environ.setdefault("JWT_ISSUER", "labtrans-auth-api")
os.environ.setdefault("JWT_AUDIENCE", "labtrans-reservas")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.database import Base, get_db
from app.main import create_app
from app.seed import seed_initial_data


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    seed_db = TestingSessionLocal()
    try:
        seed_initial_data(seed_db)
    finally:
        seed_db.close()

    app = create_app(run_seed_on_startup=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token()}"}


def make_token(
    *,
    secret: str = TEST_SECRET,
    issuer: str = "labtrans-auth-api",
    audience: str = "labtrans-reservas",
    expires_delta: timedelta = timedelta(minutes=60),
    include_user: bool = True,
) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_delta,
    }
    if include_user:
        payload["sub"] = "user-123"
        payload["email"] = "usuario@email.com"

    return jwt.encode(payload, secret, algorithm="HS256")


def reservation_payload(
    start: str = "2026-05-12T09:00:00Z", end: str = "2026-05-12T10:00:00Z"
) -> dict:
    return {
        "location_id": 1,
        "room_id": 1,
        "start_datetime": start,
        "end_datetime": end,
        "responsible": "Maria Silva",
        "coffee_required": False,
        "people_count": None,
        "description": "Reuniao de planejamento",
    }
