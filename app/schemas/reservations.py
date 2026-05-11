from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.locations import LocationRead
from app.schemas.rooms import RoomRead


class ReservationBase(BaseModel):
    location_id: int
    room_id: int
    start_datetime: datetime
    end_datetime: datetime
    responsible: str = Field(..., min_length=1, max_length=180)
    coffee_required: bool = False
    people_count: int | None = Field(default=None, gt=0)
    description: str | None = None

    @model_validator(mode="after")
    def validate_business_fields(self) -> "ReservationBase":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("Data/hora de fim precisa ser maior que a data/hora de inicio.")

        if self.coffee_required and self.people_count is None:
            raise ValueError("Quantidade de pessoas e obrigatoria quando cafe for solicitado.")

        if not self.coffee_required:
            self.people_count = None

        return self


class ReservationCreate(ReservationBase):
    pass


class ReservationUpdate(ReservationBase):
    pass


class ReservationRead(BaseModel):
    id: int
    location_id: int
    room_id: int
    start_datetime: datetime
    end_datetime: datetime
    responsible: str
    coffee_required: bool
    people_count: int | None
    description: str | None
    created_by_user_id: str
    created_by_email: str
    created_at: datetime
    updated_at: datetime | None
    location: LocationRead
    room: RoomRead

    model_config = ConfigDict(from_attributes=True)


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    deleted: int
