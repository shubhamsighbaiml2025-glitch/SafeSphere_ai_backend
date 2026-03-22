from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.safety import (
    InactivityResponseRequest,
    SafetyLocationRequest,
    SafetyModeRequest,
    SafetyStatusResponse,
    SafetyVoiceRequest,
)
from app.services.emergency_service import create_notification, trigger_emergency
from app.services.safety_monitor import contains_emergency_word, normalize_text

router = APIRouter(tags=["Safety"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_session(db: Database, current_user: dict) -> dict:
    user_id = str(current_user["_id"])
    session = db.safety_sessions.find_one({"user_id": user_id})
    if session:
        return session

    now = _now()
    session = {
        "user_id": user_id,
        "user_obj_id": current_user["_id"],
        "enabled": False,
        "ai_active": False,
        "previous_location": None,
        "current_location": None,
        "last_movement_at": now,
        "inactivity_check_state": "NONE",
        "check_prompt_at": None,
        "check_deadline": None,
        "last_voice_text": None,
        "last_emergency_id": None,
        "last_emergency_at": None,
        "created_at": now,
        "updated_at": now,
    }
    db.safety_sessions.insert_one(session)
    return db.safety_sessions.find_one({"user_id": user_id}) or session


@router.post("/safety-mode")
def set_safety_mode(
    payload: SafetyModeRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    session = _get_or_create_session(db, current_user)
    now = _now()

    if not payload.enabled:
        db.safety_sessions.update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "enabled": False,
                    "ai_active": False,
                    "inactivity_check_state": "NONE",
                    "check_prompt_at": None,
                    "check_deadline": None,
                    "updated_at": now,
                }
            },
        )
        return {"message": "Safety mode OFF. AI system stopped."}

    db.safety_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "enabled": True,
                "ai_active": True,
                "updated_at": now,
            }
        },
    )
    return {"message": "Safety mode ON. AI system activated."}


@router.get("/safety-mode/status", response_model=SafetyStatusResponse)
def get_safety_status(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> SafetyStatusResponse:
    session = _get_or_create_session(db, current_user)
    return SafetyStatusResponse(
        enabled=bool(session.get("enabled", False)),
        ai_active=bool(session.get("ai_active", False)),
        pending_safety_check=session.get("inactivity_check_state") == "PENDING",
        check_deadline=session.get("check_deadline"),
        last_movement_at=session.get("last_movement_at"),
    )


@router.post("/safety/voice-check", status_code=status.HTTP_201_CREATED)
def process_voice_detection(
    payload: SafetyVoiceRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    session = _get_or_create_session(db, current_user)
    if not session.get("enabled"):
        return {"message": "Safety mode OFF. Voice detection skipped."}

    normalized_text = normalize_text(payload.text)
    trigger = contains_emergency_word(normalized_text)
    now = _now()

    db.safety_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"last_voice_text": normalized_text, "updated_at": now}},
    )

    if not trigger:
        return {"message": "Voice processed. No emergency keyword detected."}

    db.ai_alerts.insert_one(
        {
            "user_id": str(current_user["_id"]),
            "detected_text": normalized_text,
            "trigger_word": trigger,
            "reason": "voice",
            "ai_processed_locally": True,
            "timestamp": now,
        }
    )
    create_notification(
        db=db,
        user_id=str(current_user["_id"]),
        notif_type="AI_ALERT",
        title="AI Risk Signal Detected",
        message=f"Detected keyword '{trigger}'. Monitoring escalated.",
    )
    emergency_id = trigger_emergency(
        db=db,
        user=current_user,
        source="voice",
        trigger_word=trigger,
        transcript=normalized_text,
        ai_processed_locally=True,
    )
    return {
        "message": "Emergency triggered from voice keyword.",
        "emergency_id": emergency_id,
        "trigger_word": trigger,
        "note": "No audio is stored on backend. Send text-only transcription.",
    }


@router.post("/safety/location-update")
def update_safety_location(
    payload: SafetyLocationRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    session = _get_or_create_session(db, current_user)
    if not session.get("enabled"):
        return {"message": "Safety mode OFF. Location monitoring skipped."}

    now = _now()
    new_location = {"lat": payload.latitude, "long": payload.longitude}
    update_doc = {
        "previous_location": session.get("current_location"),
        "current_location": new_location,
        "updated_at": now,
    }
    if payload.moved:
        update_doc.update(
            {
                "last_movement_at": now,
                "inactivity_check_state": "NONE",
                "check_prompt_at": None,
                "check_deadline": None,
            }
        )

    db.safety_sessions.update_one({"_id": session["_id"]}, {"$set": update_doc})
    db.location_logs.insert_one(
        {
            "user_id": str(current_user["_id"]),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "is_emergency_tracking": False,
            "emergency_id": None,
            "time": now,
        }
    )
    return {"message": "Location updated for safety monitoring."}


@router.post("/safety/inactivity-response")
def respond_inactivity_check(
    payload: InactivityResponseRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    session = _get_or_create_session(db, current_user)
    now = _now()

    if payload.is_safe:
        db.safety_sessions.update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "inactivity_check_state": "NONE",
                    "check_prompt_at": None,
                    "check_deadline": None,
                    "last_movement_at": now,
                    "updated_at": now,
                }
            },
        )
        return {"message": "Safety confirmed. Inactivity check cancelled."}

    emergency_id = trigger_emergency(
        db=db,
        user=current_user,
        source="inactivity",
        trigger_word="manual_not_safe_response",
        transcript="User marked not safe during inactivity check.",
        ai_processed_locally=True,
    )
    db.safety_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "inactivity_check_state": "TRIGGERED",
                "last_emergency_id": emergency_id,
                "last_emergency_at": now,
                "updated_at": now,
            }
        },
    )
    return {"message": "Emergency triggered.", "emergency_id": emergency_id}
