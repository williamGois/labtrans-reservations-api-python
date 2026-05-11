import logging
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.observability.metrics import (
    RESERVATIONS_JWT_EXPIRED_TOTAL,
    RESERVATIONS_JWT_MISSING_TOTAL,
    RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL,
)

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("reservations.jwt")


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        RESERVATIONS_JWT_MISSING_TOTAL.inc()
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("missing").inc()
        logger.warning(
            "JWT missing from protected request.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Token ausente."}
        )

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        RESERVATIONS_JWT_EXPIRED_TOTAL.inc()
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("expired").inc()
        logger.warning(
            "Expired JWT rejected.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Token expirado."}
        ) from None
    except jwt.InvalidIssuerError:
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("invalid_issuer").inc()
        logger.warning(
            "JWT rejected by invalid issuer.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Token invalido."}
        ) from None
    except jwt.InvalidAudienceError:
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("invalid_audience").inc()
        logger.warning(
            "JWT rejected by invalid audience.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Token invalido."}
        ) from None
    except jwt.PyJWTError:
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("invalid").inc()
        logger.warning(
            "Invalid JWT rejected.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Token invalido."}
        ) from None

    user_id = payload.get("sub") or payload.get("nameidentifier") or payload.get("nameid")
    email = payload.get("email")
    if not user_id or not email:
        RESERVATIONS_JWT_VALIDATION_FAILURE_TOTAL.labels("missing_claims").inc()
        logger.warning(
            "JWT rejected because required user claims are missing.",
            extra={"path": request.url.path, "statusCode": status.HTTP_401_UNAUTHORIZED},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token sem usuario valido."},
        )

    request.state.user_id = str(user_id)
    request.state.user_email = str(email)
    return CurrentUser(user_id=str(user_id), email=str(email))
