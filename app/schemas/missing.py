from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportMissingRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    photo_url: str | None = None
    last_seen_location: str
    time: datetime


class SeenReportRequest(BaseModel):
    person_id: str
    reporter_location: str


class MissingPersonResponse(BaseModel):
    id: str
    name: str
    photo_url: str | None
    last_seen_location: str
    time: datetime
    status: Literal["MISSING", "FOUND"]

