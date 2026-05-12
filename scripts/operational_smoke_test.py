from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

AUTH_API_URL = os.getenv("AUTH_API_URL", "http://localhost:5001").rstrip("/")
RESERVATIONS_API_URL = os.getenv("RESERVATIONS_API_URL", "http://localhost:8000").rstrip("/")


def request(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    correlation_id: str | None = None,
) -> tuple[int, dict[str, str], Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if correlation_id is not None:
        headers["X-Correlation-ID"] = correlation_id

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers), parse_body(body)
    except HTTPError as error:
        body = error.read().decode("utf-8")
        return error.code, dict(error.headers), parse_body(body)
    except URLError as error:
        raise RuntimeError(f"Service unavailable at {url}: {error}") from error


def parse_body(raw: str) -> Any:
    if not raw:
        return None
    if raw.lstrip().startswith("#"):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def pass_step(label: str, detail: str = "") -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[PASS] {label}{suffix}")


def fail_step(label: str, detail: str) -> None:
    print(f"[FAIL] {label} ({detail})")
    raise SystemExit(1)


def assert_status(label: str, expected: int, result: tuple[int, dict[str, str], Any]) -> None:
    status, _, body = result
    if status != expected:
        fail_step(label, f"expected HTTP {expected}, got HTTP {status}: {body}")
    pass_step(label, f"HTTP {status}")


def metric_value(metrics_text: str, metric_name: str) -> float:
    value = 0.0
    for line in metrics_text.splitlines():
        if line.startswith("#") or not line.startswith(metric_name):
            continue
        try:
            value += float(line.rsplit(" ", 1)[1])
        except (IndexError, ValueError):
            continue
    return value


def main() -> int:
    correlation_id = f"smoke-{int(time.time())}"

    auth_live = request("GET", f"{AUTH_API_URL}/health/live", correlation_id=correlation_id)
    assert_status("Auth live health", 200, auth_live)

    auth_ready = request("GET", f"{AUTH_API_URL}/health/ready", correlation_id=correlation_id)
    assert_status("Auth ready health", 200, auth_ready)

    reservations_live = request(
        "GET", f"{RESERVATIONS_API_URL}/health/live", correlation_id=correlation_id
    )
    assert_status("Reservations live health", 200, reservations_live)

    reservations_ready = request(
        "GET", f"{RESERVATIONS_API_URL}/health/ready", correlation_id=correlation_id
    )
    assert_status("Reservations ready health", 200, reservations_ready)

    auth_metrics = request("GET", f"{AUTH_API_URL}/metrics")
    assert_status("Auth metrics endpoint", 200, auth_metrics)

    reservations_metrics_before = request("GET", f"{RESERVATIONS_API_URL}/metrics")
    assert_status("Reservations metrics endpoint", 200, reservations_metrics_before)
    before_conflicts = metric_value(
        str(reservations_metrics_before[2]), "reservations_conflict_total"
    )

    email = f"smoke-{int(time.time())}@email.com"
    password = "Smoke" + "Credential" + str(int(time.time())) + "!"
    register = request(
        "POST",
        f"{AUTH_API_URL}/api/auth/register",
        payload={"email": email, "password": password},
        correlation_id=correlation_id,
    )
    assert_status("User registration", 201, register)

    login = request(
        "POST",
        f"{AUTH_API_URL}/api/auth/login",
        payload={"email": email, "password": password},
        correlation_id=correlation_id,
    )
    assert_status("Login returned JWT", 200, login)
    token = login[2].get("accessToken")
    if not token:
        fail_step("Login returned JWT", "accessToken missing")

    assert_status(
        "Reservations API rejected missing token",
        401,
        request("GET", f"{RESERVATIONS_API_URL}/api/reservations", correlation_id=correlation_id),
    )
    assert_status(
        "Invalid JWT rejected",
        401,
        request(
            "GET",
            f"{RESERVATIONS_API_URL}/api/reservations",
            token="invalid-token",
            correlation_id=correlation_id,
        ),
    )
    assert_status(
        "Valid JWT accepted by reservations API",
        200,
        request(
            "GET",
            f"{RESERVATIONS_API_URL}/api/reservations",
            token=token,
            correlation_id=correlation_id,
        ),
    )

    locations = request("GET", f"{RESERVATIONS_API_URL}/api/locations", token=token)[2]
    rooms = request("GET", f"{RESERVATIONS_API_URL}/api/rooms", token=token)[2]
    if not locations or not rooms:
        fail_step("Seed data available", "expected at least one location and one room")

    start = datetime.now(tz=UTC).replace(microsecond=0) + timedelta(days=2)
    end = start + timedelta(hours=1)
    payload = {
        "location_id": locations[0]["id"],
        "room_id": rooms[0]["id"],
        "start_datetime": start.isoformat().replace("+00:00", "Z"),
        "end_datetime": end.isoformat().replace("+00:00", "Z"),
        "responsible": "Smoke Test",
        "coffee_required": False,
        "people_count": None,
        "description": "Operational smoke test",
    }

    created = request(
        "POST",
        f"{RESERVATIONS_API_URL}/api/reservations",
        payload=payload,
        token=token,
        correlation_id=correlation_id,
    )
    assert_status("Reservation created", 201, created)
    reservation_id = created[2]["id"]

    conflict = request(
        "POST",
        f"{RESERVATIONS_API_URL}/api/reservations",
        payload=payload,
        token=token,
        correlation_id=correlation_id,
    )
    assert_status("Schedule conflict returned 409", 409, conflict)

    reservations_metrics_after = request("GET", f"{RESERVATIONS_API_URL}/metrics")
    after_conflicts = metric_value(
        str(reservations_metrics_after[2]), "reservations_conflict_total"
    )
    if after_conflicts <= before_conflicts:
        fail_step("Conflict metric increased", "reservations_conflict_total did not increase")
    pass_step("Conflict metric increased", f"{before_conflicts} -> {after_conflicts}")

    delete = request(
        "DELETE",
        f"{RESERVATIONS_API_URL}/api/reservations/{reservation_id}",
        token=token,
        correlation_id=correlation_id,
    )
    assert_status("Reservation deleted", 204, delete)

    returned_correlation = auth_live[1].get("X-Correlation-ID")
    if returned_correlation != correlation_id:
        fail_step(
            "Correlation ID propagated", f"expected {correlation_id}, got {returned_correlation}"
        )
    pass_step("Correlation ID propagated", returned_correlation)

    print("Operational smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
