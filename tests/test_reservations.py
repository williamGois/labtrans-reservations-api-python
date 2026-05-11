from datetime import timedelta

import pytest

from tests.conftest import make_token, reservation_payload


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_locations_with_valid_token(client, auth_headers):
    response = client.get("/api/locations", headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_list_rooms_with_valid_token(client, auth_headers):
    response = client.get("/api/rooms", headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_list_reservations_with_valid_token(client, auth_headers):
    response = client.get("/api/reservations", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_missing_token_returns_401(client):
    response = client.get("/api/reservations")

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/api/reservations", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("token", "case_name"),
    [
        (make_token(expires_delta=timedelta(minutes=-1)), "expired"),
        (make_token(issuer="issuer-errado"), "wrong issuer"),
        (make_token(audience="audience-errada"), "wrong audience"),
        (make_token(secret="secret-errado-com-tamanho-suficiente"), "wrong secret"),
        (make_token(include_user=False), "missing user claims"),
    ],
)
def test_invalid_jwt_variants_return_401(client, token, case_name):
    response = client.get("/api/reservations", headers=bearer(token))

    assert response.status_code == 401, case_name


def test_create_valid_reservation(client, auth_headers):
    response = client.post("/api/reservations", json=reservation_payload(), headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["responsible"] == "Maria Silva"
    assert body["created_by_email"] == "usuario@email.com"
    assert body["location"]["name"] == "Matriz Florianopolis"
    assert body["room"]["name"] == "Sala Azul"


@pytest.mark.parametrize(
    "missing_field", ["location_id", "room_id", "start_datetime", "end_datetime", "responsible"]
)
def test_create_reservation_missing_required_field_returns_400(client, auth_headers, missing_field):
    payload = reservation_payload()
    payload.pop(missing_field)

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["message"] == "Dados invalidos."


def test_create_reservation_with_unknown_location_returns_404(client, auth_headers):
    payload = reservation_payload()
    payload["location_id"] = 999

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["message"] == "Local nao encontrado."


def test_create_reservation_with_unknown_room_returns_404(client, auth_headers):
    payload = reservation_payload()
    payload["room_id"] = 999

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["message"] == "Sala nao encontrada."


def test_create_reservation_with_end_before_start_fails(client, auth_headers):
    payload = reservation_payload(start="2026-05-12T10:00:00Z", end="2026-05-12T09:00:00Z")

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["message"] == "Dados invalidos."


def test_create_reservation_with_end_equal_to_start_fails(client, auth_headers):
    payload = reservation_payload(start="2026-05-12T10:00:00Z", end="2026-05-12T10:00:00Z")

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["message"] == "Dados invalidos."


def test_create_reservation_with_conflict_fails(client, auth_headers):
    client.post("/api/reservations", json=reservation_payload(), headers=auth_headers)

    response = client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-12T09:30:00Z", end="2026-05-12T10:30:00Z"),
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["conflictingReservationId"] == 1


def test_update_reservation_with_conflict_fails(client, auth_headers):
    client.post("/api/reservations", json=reservation_payload(), headers=auth_headers)
    created = client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-12T11:00:00Z", end="2026-05-12T12:00:00Z"),
        headers=auth_headers,
    ).json()

    response = client.put(
        f"/api/reservations/{created['id']}",
        json=reservation_payload(start="2026-05-12T09:15:00Z", end="2026-05-12T09:45:00Z"),
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["conflictingReservationId"] == 1


def test_update_reservation_valid_payload_works(client, auth_headers):
    created = client.post(
        "/api/reservations", json=reservation_payload(), headers=auth_headers
    ).json()
    payload = reservation_payload(start="2026-05-12T10:00:00Z", end="2026-05-12T11:00:00Z")
    payload["responsible"] = "Joao Editado"

    response = client.put(f"/api/reservations/{created['id']}", json=payload, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["responsible"] == "Joao Editado"


def test_update_reservation_ignores_itself_in_conflict_validation(client, auth_headers):
    created = client.post(
        "/api/reservations", json=reservation_payload(), headers=auth_headers
    ).json()

    response = client.put(
        f"/api/reservations/{created['id']}", json=reservation_payload(), headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_delete_reservation_works(client, auth_headers):
    created = client.post(
        "/api/reservations", json=reservation_payload(), headers=auth_headers
    ).json()

    delete_response = client.delete(f"/api/reservations/{created['id']}", headers=auth_headers)
    list_response = client.get("/api/reservations", headers=auth_headers)

    assert delete_response.status_code == 204
    assert list_response.json() == []


def test_get_unknown_reservation_returns_404(client, auth_headers):
    response = client.get("/api/reservations/999", headers=auth_headers)

    assert response.status_code == 404


def test_delete_unknown_reservation_returns_404(client, auth_headers):
    response = client.delete("/api/reservations/999", headers=auth_headers)

    assert response.status_code == 404


def test_coffee_true_without_people_count_fails(client, auth_headers):
    payload = reservation_payload()
    payload["coffee_required"] = True
    payload["people_count"] = None

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["message"] == "Dados invalidos."


def test_coffee_true_with_zero_people_count_fails(client, auth_headers):
    payload = reservation_payload()
    payload["coffee_required"] = True
    payload["people_count"] = 0

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["message"] == "Dados invalidos."


def test_coffee_false_allows_null_people_count(client, auth_headers):
    payload = reservation_payload()
    payload["coffee_required"] = False
    payload["people_count"] = None

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["people_count"] is None


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-05-13T10:00:00Z", "2026-05-13T11:00:00Z"),
        ("2026-05-13T10:30:00Z", "2026-05-13T11:30:00Z"),
        ("2026-05-13T09:30:00Z", "2026-05-13T10:30:00Z"),
        ("2026-05-13T09:00:00Z", "2026-05-13T12:00:00Z"),
    ],
)
def test_conflicting_time_windows_fail_for_same_room_and_location(client, auth_headers, start, end):
    client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-13T10:00:00Z", end="2026-05-13T11:00:00Z"),
        headers=auth_headers,
    )

    response = client.post(
        "/api/reservations", json=reservation_payload(start=start, end=end), headers=auth_headers
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Ja existe uma reserva para esta sala, local e horario."


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-05-13T09:00:00Z", "2026-05-13T10:00:00Z"),
        ("2026-05-13T11:00:00Z", "2026-05-13T12:00:00Z"),
    ],
)
def test_adjacent_time_windows_pass_for_same_room_and_location(client, auth_headers, start, end):
    client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-13T10:00:00Z", end="2026-05-13T11:00:00Z"),
        headers=auth_headers,
    )

    response = client.post(
        "/api/reservations", json=reservation_payload(start=start, end=end), headers=auth_headers
    )

    assert response.status_code == 201


def test_same_time_passes_for_different_room(client, auth_headers):
    client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-14T10:00:00Z", end="2026-05-14T11:00:00Z"),
        headers=auth_headers,
    )
    payload = reservation_payload(start="2026-05-14T10:00:00Z", end="2026-05-14T11:00:00Z")
    payload["room_id"] = 2

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 201


def test_same_time_passes_for_different_location(client, auth_headers):
    client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-14T12:00:00Z", end="2026-05-14T13:00:00Z"),
        headers=auth_headers,
    )
    payload = reservation_payload(start="2026-05-14T12:00:00Z", end="2026-05-14T13:00:00Z")
    payload["location_id"] = 2
    payload["room_id"] = 3

    response = client.post("/api/reservations", json=payload, headers=auth_headers)

    assert response.status_code == 201


def test_update_to_overlap_another_reservation_fails(client, auth_headers):
    client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-15T10:00:00Z", end="2026-05-15T11:00:00Z"),
        headers=auth_headers,
    )
    second = client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-15T12:00:00Z", end="2026-05-15T13:00:00Z"),
        headers=auth_headers,
    ).json()

    response = client.put(
        f"/api/reservations/{second['id']}",
        json=reservation_payload(start="2026-05-15T10:30:00Z", end="2026-05-15T11:30:00Z"),
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_bulk_delete_multiple_reservations(client, auth_headers):
    first = client.post(
        "/api/reservations", json=reservation_payload(), headers=auth_headers
    ).json()
    second = client.post(
        "/api/reservations",
        json=reservation_payload(start="2026-05-12T11:00:00Z", end="2026-05-12T12:00:00Z"),
        headers=auth_headers,
    ).json()

    response = client.post(
        "/api/reservations/bulk-delete",
        json={"ids": [first["id"], second["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert client.get("/api/reservations", headers=auth_headers).json() == []


def test_bulk_delete_empty_list_returns_400(client, auth_headers):
    response = client.post("/api/reservations/bulk-delete", json={"ids": []}, headers=auth_headers)

    assert response.status_code == 400


def test_bulk_delete_ignores_unknown_ids_and_deletes_existing(client, auth_headers):
    created = client.post(
        "/api/reservations", json=reservation_payload(), headers=auth_headers
    ).json()

    response = client.post(
        "/api/reservations/bulk-delete", json={"ids": [created["id"], 999]}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
