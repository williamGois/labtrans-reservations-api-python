from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import delete

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import create_app
from app.models import Reservation
from app.seed import seed_initial_data

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ISSUER = os.getenv("JWT_ISSUER", "labtrans-auth-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "labtrans-reservas")


def make_token() -> str:
    now = datetime.now(tz=UTC)
    return jwt.encode(
        {
            "sub": "ci-user-123",
            "email": "ci-reservations@example.test",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def assert_status(label: str, expected: int, actual: int, body: Any = None) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, got HTTP {actual}: {body}")
    print(f"[PASS] {label} (HTTP {actual})")


def reservation_payload(location_id: int, room_id: int, start: datetime) -> dict[str, Any]:
    return {
        "location_id": location_id,
        "room_id": room_id,
        "start_datetime": iso(start),
        "end_datetime": iso(start + timedelta(hours=1)),
        "responsible": "CI PostgreSQL Smoke",
        "coffee_required": False,
        "people_count": None,
        "description": "Reserva criada pelo smoke test de CI com PostgreSQL.",
    }


def main() -> int:
    db = SessionLocal()
    try:
        seed_initial_data(db)
        db.execute(delete(Reservation).where(Reservation.responsible == "CI PostgreSQL Smoke"))
        db.commit()
    finally:
        db.close()

    app = create_app(run_seed_on_startup=False)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {make_token()}", "X-Correlation-ID": "ci-postgres-smoke"}
    created_ids: list[int] = []

    try:
        response = client.get("/health/ready", headers={"X-Correlation-ID": "ci-postgres-smoke"})
        assert_status(
            "Reservations ready health against PostgreSQL", 200, response.status_code, response.text
        )
        if response.headers.get("X-Correlation-ID") != "ci-postgres-smoke":
            raise AssertionError("Reservations API did not preserve X-Correlation-ID")
        print("[PASS] Reservations API preserves correlation id")

        response = client.get("/api/locations", headers=headers)
        assert_status("List locations against PostgreSQL", 200, response.status_code, response.text)
        locations = response.json()
        response = client.get("/api/rooms", headers=headers)
        assert_status("List rooms against PostgreSQL", 200, response.status_code, response.text)
        rooms = response.json()
        if not locations or not rooms:
            raise AssertionError("Seed data was not available in PostgreSQL")

        room = rooms[0]
        start = datetime.now(tz=UTC).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=20
        )
        payload = reservation_payload(room["location_id"], room["id"], start)

        response = client.post("/api/reservations", json=payload, headers=headers)
        assert_status(
            "Create reservation against PostgreSQL", 201, response.status_code, response.text
        )
        created_ids.append(response.json()["id"])

        response = client.post("/api/reservations", json=payload, headers=headers)
        assert_status(
            "Reject conflict against PostgreSQL", 409, response.status_code, response.text
        )
        if "conflictingReservationId" not in response.json():
            raise AssertionError("Conflict response did not include conflictingReservationId")

        updated = payload | {"responsible": "CI PostgreSQL Smoke Edited"}
        response = client.put(f"/api/reservations/{created_ids[0]}", json=updated, headers=headers)
        assert_status(
            "Update reservation against PostgreSQL", 200, response.status_code, response.text
        )

        response = client.delete(f"/api/reservations/{created_ids.pop()}", headers=headers)
        assert_status(
            "Delete reservation against PostgreSQL", 204, response.status_code, response.text
        )

        response = client.get("/metrics")
        assert_status("Reservations metrics endpoint", 200, response.status_code, response.text)
        if "reservations_conflict_total" not in response.text:
            raise AssertionError("Metrics did not include reservations_conflict_total")

        print("[PASS] Reservations PostgreSQL integration smoke completed")
        return 0
    finally:
        for reservation_id in created_ids:
            client.delete(f"/api/reservations/{reservation_id}", headers=headers)


if __name__ == "__main__":
    sys.exit(main())
