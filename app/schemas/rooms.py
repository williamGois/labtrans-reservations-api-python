from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    location_id: int
    name: str = Field(..., min_length=1, max_length=160)
    capacity: int = Field(..., gt=0)
    active: bool = True


class RoomRead(BaseModel):
    id: int
    location_id: int
    name: str
    capacity: int
    active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
