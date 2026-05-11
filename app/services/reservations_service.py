import logging

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.models import Location, Reservation, Room
from app.observability.metrics import RESERVATIONS_CONFLICT_TOTAL
from app.schemas.reservations import ReservationCreate, ReservationUpdate
from app.security.jwt import CurrentUser

CONFLICT_MESSAGE = "Ja existe uma reserva para esta sala, local e horario."
logger = logging.getLogger("reservations.domain")


def reservation_query() -> Select[tuple[Reservation]]:
    return select(Reservation).options(
        joinedload(Reservation.location), joinedload(Reservation.room)
    )


def get_reservation_or_404(db: Session, reservation_id: int) -> Reservation:
    reservation = db.scalar(reservation_query().where(Reservation.id == reservation_id))
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Reserva nao encontrada."}
        )
    return reservation


def validate_location_and_room(
    db: Session, location_id: int, room_id: int
) -> tuple[Location, Room]:
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Local nao encontrado."}
        )

    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Sala nao encontrada."}
        )

    if room.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Sala nao pertence ao local informado."},
        )

    if not room.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Sala inativa nao pode receber reservas."},
        )

    return location, room


def find_conflict(
    db: Session,
    payload: ReservationCreate | ReservationUpdate,
    ignore_reservation_id: int | None = None,
) -> Reservation | None:
    query = select(Reservation).where(
        Reservation.location_id == payload.location_id,
        Reservation.room_id == payload.room_id,
        payload.start_datetime < Reservation.end_datetime,
        payload.end_datetime > Reservation.start_datetime,
    )

    if ignore_reservation_id is not None:
        query = query.where(Reservation.id != ignore_reservation_id)

    return db.scalar(query)


def raise_conflict(conflicting: Reservation) -> None:
    RESERVATIONS_CONFLICT_TOTAL.inc()
    logger.warning(
        "Schedule conflict detected.",
        extra={
            "event": "reservation_conflict",
            "statusCode": status.HTTP_409_CONFLICT,
        },
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": CONFLICT_MESSAGE, "conflictingReservationId": conflicting.id},
    )


def create_reservation(
    db: Session, payload: ReservationCreate, current_user: CurrentUser
) -> Reservation:
    validate_location_and_room(db, payload.location_id, payload.room_id)
    conflicting = find_conflict(db, payload)
    if conflicting is not None:
        raise_conflict(conflicting)

    reservation = Reservation(
        location_id=payload.location_id,
        room_id=payload.room_id,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        responsible=payload.responsible.strip(),
        coffee_required=payload.coffee_required,
        people_count=payload.people_count,
        description=payload.description,
        created_by_user_id=current_user.user_id,
        created_by_email=current_user.email,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return get_reservation_or_404(db, reservation.id)


def update_reservation(db: Session, reservation_id: int, payload: ReservationUpdate) -> Reservation:
    reservation = get_reservation_or_404(db, reservation_id)
    validate_location_and_room(db, payload.location_id, payload.room_id)
    conflicting = find_conflict(db, payload, ignore_reservation_id=reservation_id)
    if conflicting is not None:
        raise_conflict(conflicting)

    reservation.location_id = payload.location_id
    reservation.room_id = payload.room_id
    reservation.start_datetime = payload.start_datetime
    reservation.end_datetime = payload.end_datetime
    reservation.responsible = payload.responsible.strip()
    reservation.coffee_required = payload.coffee_required
    reservation.people_count = payload.people_count
    reservation.description = payload.description

    db.commit()
    db.refresh(reservation)
    return get_reservation_or_404(db, reservation.id)
