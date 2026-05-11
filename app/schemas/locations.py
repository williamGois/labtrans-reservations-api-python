from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    address: str = Field(..., min_length=1, max_length=255)


class LocationRead(BaseModel):
    id: int
    name: str
    address: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
