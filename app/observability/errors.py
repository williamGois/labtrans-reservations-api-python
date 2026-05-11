from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.observability.correlation import get_correlation_id


def title_for_status(status_code: int) -> str:
    if status_code == 400:
        return "Validation error"
    if status_code == 401:
        return "Unauthorized"
    if status_code == 404:
        return "Not found"
    if status_code == 409:
        return "Schedule conflict"

    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def problem_response(
    request: Request,
    status_code: int,
    detail: str,
    *,
    title: str | None = None,
    headers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "title": title or title_for_status(status_code),
        "status": status_code,
        "detail": detail,
        "message": detail,
        "correlationId": get_correlation_id(),
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
    }
    if extra:
        content.update(extra)

    response = JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=headers,
    )
    return response
