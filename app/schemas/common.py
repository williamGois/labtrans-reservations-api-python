from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class ConflictResponse(BaseModel):
    message: str
    conflictingReservationId: int
