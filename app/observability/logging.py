from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.config import Settings
from app.observability.correlation import get_correlation_id

SERVICE_NAME = "labtrans-reservations-api-python"


class JsonLogFormatter(logging.Formatter):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "serviceName": SERVICE_NAME,
            "environment": self.settings.app_environment,
            "correlationId": getattr(record, "correlationId", None) or get_correlation_id(),
            "logger": record.name,
        }

        for field in (
            "method",
            "path",
            "route",
            "statusCode",
            "elapsedMs",
            "userId",
            "userEmail",
            "event",
            "errorType",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter(settings))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    logging.getLogger("uvicorn.access").disabled = True
