from prometheus_client import Counter, Gauge, Histogram

SERVICE_NAME = "labtrans-reservations-api-python"

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the Reservations API.",
    ["method", "route", "status_code", "service"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds for the Reservations API.",
    ["method", "route", "status_code", "service"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress for the Reservations API.",
    ["method", "route", "service"],
)

RESERVATIONS_CREATED_TOTAL = Counter("reservations_created_total", "Reservations created.")
RESERVATIONS_UPDATED_TOTAL = Counter("reservations_updated_total", "Reservations updated.")
RESERVATIONS_DELETED_TOTAL = Counter("reservations_deleted_total", "Reservations deleted.")
RESERVATIONS_CONFLICT_TOTAL = Counter(
    "reservations_conflict_total", "Reservations rejected by schedule conflict."
)
RESERVATIONS_BULK_DELETED_TOTAL = Counter(
    "reservations_bulk_deleted_total", "Reservations deleted by bulk endpoint."
)
RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL = Counter(
    "reservations_jwt_validation_failure_total",
    "JWT validation failures.",
    ["error_type"],
)
RESERVATIONS_JWT_MISSING_TOTAL = Counter("reservations_jwt_missing_total", "Missing JWT tokens.")
RESERVATIONS_JWT_EXPIRED_TOTAL = Counter("reservations_jwt_expired_total", "Expired JWT tokens.")
RESERVATIONS_DATABASE_ERRORS_TOTAL = Counter(
    "reservations_database_errors_total", "Database errors detected by the Reservations API."
)
