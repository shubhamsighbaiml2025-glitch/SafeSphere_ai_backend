from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.notification import (
    AddNotificationRequest,
    MarkReadRequest,
    NotificationResponse,
)
from app.utils.serializers import serialize_document

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(
    current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)
) -> list[NotificationResponse]:
    user_id = str(current_user["_id"])
    docs = db.notifications.find({"user_id": user_id}).sort("timestamp", -1)
    result: list[NotificationResponse] = []

    for doc in docs:
        notif = serialize_document(doc)
        result.append(
            NotificationResponse(
                id=notif["id"],
                user_id=notif["user_id"],
                type=notif["type"],
                title=notif["title"],
                message=notif["message"],
                timestamp=notif["timestamp"],
                status=notif["status"],
            )
        )
    return result


@router.post("/add-notification", status_code=status.HTTP_201_CREATED)
def add_notification(
    payload: AddNotificationRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    _ = current_user
    db.notifications.insert_one(
        {
            "user_id": payload.user_id,
            "type": payload.type,
            "title": payload.title,
            "message": payload.message,
            "timestamp": datetime.now(timezone.utc),
            "status": "UNREAD",
        }
    )
    return {"message": "Notification added"}


@router.post("/mark-read")
def mark_read(
    payload: MarkReadRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    try:
        notification_id = ObjectId(payload.notification_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification_id"
        ) from exc

    result = db.notifications.update_one(
        {"_id": notification_id, "user_id": str(current_user["_id"])},
        {"$set": {"status": "READ"}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}

