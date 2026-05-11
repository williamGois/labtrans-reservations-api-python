from contextvars import ContextVar
from uuid import uuid4

HEADER_NAME = "X-Correlation-ID"
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_MAX_LENGTH = 128


def normalize_correlation_id(value: str | None) -> str:
    if value is None or not value.strip():
        return uuid4().hex

    return value.strip()[:_MAX_LENGTH]


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    value = _correlation_id.get()
    if value:
        return value

    generated = uuid4().hex
    set_correlation_id(generated)
    return generated
