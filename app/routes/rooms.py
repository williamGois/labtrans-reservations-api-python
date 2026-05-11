from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Location, Room
from app.schemas.rooms import RoomCreate, RoomRead
from app.security.jwt import get_current_user

router = APIRouter(prefix="/api/rooms", tags=["rooms"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[RoomRead])
def list_rooms(
    location_id: int | None = Query(default=None), db: Session = Depends(get_db)
) -> list[Room]:
    query = select(Room).order_by(Room.name)
    if location_id is not None:
        query = query.where(Room.location_id == location_id)
    return list(db.scalars(query))


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)) -> Room:
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Local nao encontrado."}
        )

    room = Room(
        location_id=payload.location_id,
        name=payload.name.strip(),
        capacity=payload.capacity,
        active=payload.active,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room
