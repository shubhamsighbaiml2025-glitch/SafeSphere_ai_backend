from datetime import datetime

from pydantic import BaseModel, Field


class SafetyModeRequest(BaseModel):
    enabled: bool


class SafetyLocationRequest(BaseModel):
    latitude: float
    longitude: float
    moved: bool = True


class SafetyVoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class InactivityResponseRequest(BaseModel):
    is_safe: bool = True


class SafetyStatusResponse(BaseModel):
    enabled: bool
    ai_active: bool
    pending_safety_check: bool
    check_deadline: datetime | None = None
    last_movement_at: datetime | None = None
