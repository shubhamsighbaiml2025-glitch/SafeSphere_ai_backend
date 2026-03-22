from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LocationData(BaseModel):
    lat: float
    long: float


class SOSRequest(BaseModel):
    location: LocationData
    source: Literal["manual", "voice", "inactivity"] = "manual"
    trigger_word: str | None = None
    transcript: str | None = None
    ai_processed_locally: bool = True


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    is_emergency_tracking: bool = False
    emergency_id: str | None = None


class StopEmergencyRequest(BaseModel):
    emergency_id: str


class AIAlertRequest(BaseModel):
    detected_text: str = Field(min_length=1, max_length=1000)
    trigger_word: str = Field(min_length=1, max_length=80)
    reason: Literal["voice", "inactivity", "manual"] = "voice"
    ai_processed_locally: bool = True


class EmergencyResponse(BaseModel):
    id: str
    user_id: str
    location: LocationData
    status: Literal["ACTIVE", "SAFE"]
    timestamp: datetime
