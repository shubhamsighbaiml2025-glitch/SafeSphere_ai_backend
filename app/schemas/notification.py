from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AddNotificationRequest(BaseModel):
    user_id: str
    type: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=2, max_length=1000)


class MarkReadRequest(BaseModel):
    notification_id: str


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    timestamp: datetime
    status: Literal["READ", "UNREAD"]

