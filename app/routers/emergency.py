from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.emergency import LocationUpdateRequest, SOSRequest, StopEmergencyRequest

router = APIRouter(tags=["Emergency"])


def _create_notification(
    db: Database, user_id: str, notif_type: str, title: str, message: str
) -> None:
    db.notifications.insert_one(
        {
            "user_id": user_id,
            "type": notif_type,
            "title": title,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "status": "UNREAD",
        }
    )


@router.post("/sos", status_code=status.HTTP_201_CREATED)
def trigger_sos(
    payload: SOSRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    user_id = str(current_user["_id"])
    emergency_doc = {
        "user_id": user_id,
        "location": {"lat": payload.location.lat, "long": payload.location.long},
        "status": "ACTIVE",
        "timestamp": datetime.now(timezone.utc),
    }
    result = db.emergencies.insert_one(emergency_doc)

    _create_notification(
        db=db,
        user_id=user_id,
        notif_type="EMERGENCY",
        title="SOS Activated",
        message="Emergency alert has been triggered.",
    )
    return {"message": "SOS triggered", "emergency_id": str(result.inserted_id)}


@router.post("/location-update")
def update_location(
    payload: LocationUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    db.location_logs.insert_one(
        {
            "user_id": str(current_user["_id"]),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "time": datetime.now(timezone.utc),
        }
    )
    return {"message": "Location updated"}


@router.post("/stop")
def stop_emergency(
    payload: StopEmergencyRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    try:
        emergency_id = ObjectId(payload.emergency_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid emergency_id"
        ) from exc

    result = db.emergencies.update_one(
        {"_id": emergency_id, "user_id": str(current_user["_id"])},
        {"$set": {"status": "SAFE"}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency not found",
        )

    _create_notification(
        db=db,
        user_id=str(current_user["_id"]),
        notif_type="EMERGENCY",
        title="Emergency Marked Safe",
        message="Emergency status updated to SAFE.",
    )
    return {"message": "Emergency stopped"}

