from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LocationData(BaseModel):
    lat: float
    long: float


class SOSRequest(BaseModel):
    location: LocationData


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float


class StopEmergencyRequest(BaseModel):
    emergency_id: str


class EmergencyResponse(BaseModel):
    id: str
    user_id: str
    location: LocationData
    status: Literal["ACTIVE", "SAFE"]
    timestamp: datetime

