from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GeoPoint(BaseModel):
    lat: float | None = None
    lon: float | None = None


class SeatBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    gridX: int
    gridY: int
    seatType: str | None = None
    attributes: dict | None = None
    active: bool


class RoomBrief(BaseModel):
    id: UUID
    name: str
    allowFullRoomBooking: bool
    features: list[str] = Field(default_factory=list)


class RoomFull(RoomBrief):
    gridWidth: int | None = None
    gridHeight: int | None = None
    seats: list[SeatBrief] = Field(default_factory=list)


class VenueListItem(BaseModel):
    id: UUID
    name: str
    address: str
    features: list[str] = Field(default_factory=list)
    availableWorkplaces: int


class VenueFull(BaseModel):
    id: UUID
    name: str
    address: str
    timezone: str
    location: GeoPoint = GeoPoint()
    features: list[str] = Field(default_factory=list)
    rooms: list[RoomBrief] = Field(default_factory=list)


class VenueCreate(BaseModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    timezone: str = "Europe/Moscow"
    features: list[str] = Field(default_factory=list)


class RoomLayoutSeatInput(BaseModel):
    id: UUID | None = None
    label: str
    gridX: int
    gridY: int
    seatType: str | None = None
    attributes: dict | None = None
    active: bool = True


class RoomLayoutUpdate(BaseModel):
    allowFullRoomBooking: bool | None = None
    seats: list[RoomLayoutSeatInput] = Field(default_factory=list)
