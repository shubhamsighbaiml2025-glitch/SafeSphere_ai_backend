from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.emergency import (
    AIAlertRequest,
    LocationUpdateRequest,
    SOSRequest,
    StopEmergencyRequest,
)
from app.services.emergency_service import create_notification, trigger_emergency

router = APIRouter(tags=["Emergency"])


@router.post("/sos", status_code=status.HTTP_201_CREATED)
def trigger_sos(
    payload: SOSRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    emergency_id = trigger_emergency(
        db=db,
        user=current_user,
        source=payload.source,
        trigger_word=payload.trigger_word,
        transcript=payload.transcript,
        location={"lat": payload.location.lat, "long": payload.location.long},
        ai_processed_locally=payload.ai_processed_locally,
    )
    return {"message": "SOS triggered", "emergency_id": emergency_id}


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
            "is_emergency_tracking": payload.is_emergency_tracking,
            "emergency_id": payload.emergency_id,
            "time": datetime.now(timezone.utc),
        }
    )
    return {"message": "Location updated"}


@router.post("/ai-alert", status_code=status.HTTP_201_CREATED)
def create_ai_alert(
    payload: AIAlertRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    user_id = str(current_user["_id"])
    db.ai_alerts.insert_one(
        {
            "user_id": user_id,
            "detected_text": payload.detected_text,
            "trigger_word": payload.trigger_word,
            "reason": payload.reason,
            "ai_processed_locally": payload.ai_processed_locally,
            "timestamp": datetime.now(timezone.utc),
        }
    )
    create_notification(
        db=db,
        user_id=user_id,
        notif_type="AI_ALERT",
        title="AI Risk Signal Detected",
        message=f"Detected keyword '{payload.trigger_word}'. Monitoring escalated.",
    )
    return {"message": "AI alert logged"}


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

    create_notification(
        db=db,
        user_id=str(current_user["_id"]),
        notif_type="EMERGENCY",
        title="Emergency Marked Safe",
        message="Emergency status updated to SAFE.",
    )
    return {"message": "Emergency stopped"}
