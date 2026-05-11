import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reservation
from app.observability.metrics import (
    RESERVATIONS_BULK_DELETED_TOTAL,
    RESERVATIONS_CREATED_TOTAL,
    RESERVATIONS_DELETED_TOTAL,
    RESERVATIONS_UPDATED_TOTAL,
)
from app.schemas.reservations import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    ReservationCreate,
    ReservationRead,
    ReservationUpdate,
)
from app.security.jwt import CurrentUser, get_current_user
from app.services.reservations_service import (
    create_reservation,
    get_reservation_or_404,
    reservation_query,
    update_reservation,
)

router = APIRouter(prefix="/api/reservations", tags=["reservations"])
logger = logging.getLogger("reservations.api")


@router.get("", response_model=list[ReservationRead])
def list_reservations(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[Reservation]:
    return list(db.scalars(reservation_query().order_by(Reservation.start_datetime)))


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_reservations(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> BulkDeleteResponse:
    existing_ids = set(db.scalars(select(Reservation.id).where(Reservation.id.in_(payload.ids))))
    if not existing_ids:
        return BulkDeleteResponse(deleted=0)

    result = db.execute(delete(Reservation).where(Reservation.id.in_(existing_ids)))
    db.commit()
    deleted = result.rowcount or 0
    RESERVATIONS_BULK_DELETED_TOTAL.inc(deleted)
    logger.info("Reservations bulk deleted.", extra={"event": "reservations_bulk_deleted"})
    return BulkDeleteResponse(deleted=deleted)


@router.get("/{reservation_id}", response_model=ReservationRead)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Reservation:
    return get_reservation_or_404(db, reservation_id)


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create_reservation_endpoint(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Reservation:
    reservation = create_reservation(db, payload, current_user)
    RESERVATIONS_CREATED_TOTAL.inc()
    logger.info(
        "Reservation created.",
        extra={"event": "reservation_created", "userId": current_user.user_id},
    )
    return reservation


@router.put("/{reservation_id}", response_model=ReservationRead)
def update_reservation_endpoint(
    reservation_id: int,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Reservation:
    reservation = update_reservation(db, reservation_id, payload)
    RESERVATIONS_UPDATED_TOTAL.inc()
    logger.info("Reservation updated.", extra={"event": "reservation_updated"})
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation_endpoint(
    reservation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    reservation = get_reservation_or_404(db, reservation_id)
    db.delete(reservation)
    db.commit()
    RESERVATIONS_DELETED_TOTAL.inc()
    logger.info("Reservation deleted.", extra={"event": "reservation_deleted"})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
