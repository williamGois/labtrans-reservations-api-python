from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Location
from app.schemas.locations import LocationCreate, LocationRead
from app.security.jwt import get_current_user

router = APIRouter(
    prefix="/api/locations", tags=["locations"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[LocationRead])
def list_locations(db: Session = Depends(get_db)) -> list[Location]:
    return list(db.scalars(select(Location).order_by(Location.name)))


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreate, db: Session = Depends(get_db)) -> Location:
    location = Location(name=payload.name.strip(), address=payload.address.strip())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location
