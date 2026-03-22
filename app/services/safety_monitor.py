import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import get_db
from app.services.emergency_service import create_notification, trigger_emergency

CHECK_INTERVAL_SECONDS = 30
INACTIVITY_MINUTES = 15
SAFETY_PROMPT_MINUTES = 5

_monitor_task: asyncio.Task | None = None
_monitor_running = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def contains_emergency_word(normalized_text: str) -> str | None:
    trigger_phrases = ("help", "danger", "save me")
    for phrase in trigger_phrases:
        if phrase in normalized_text:
            return phrase
    return None


def _process_inactivity_checks() -> None:
    db = get_db()
    now = _utc_now()
    sessions = db.safety_sessions.find({"enabled": True})

    for session in sessions:
        user_id = session.get("user_id")
        if not user_id:
            continue

        last_movement_at = session.get("last_movement_at")
        check_state = session.get("inactivity_check_state", "NONE")
        check_deadline = session.get("check_deadline")

        if (
            isinstance(last_movement_at, datetime)
            and check_state == "NONE"
            and now - last_movement_at >= timedelta(minutes=INACTIVITY_MINUTES)
        ):
            deadline = now + timedelta(minutes=SAFETY_PROMPT_MINUTES)
            db.safety_sessions.update_one(
                {"_id": session["_id"]},
                {
                    "$set": {
                        "inactivity_check_state": "PENDING",
                        "check_prompt_at": now,
                        "check_deadline": deadline,
                        "updated_at": now,
                    }
                },
            )
            create_notification(
                db=db,
                user_id=user_id,
                notif_type="SAFETY_CHECK",
                title="Are you safe?",
                message=(
                    "No movement detected for 15 minutes. "
                    "Please confirm safety within 5 minutes."
                ),
            )
            continue

        if (
            check_state == "PENDING"
            and isinstance(check_deadline, datetime)
            and now >= check_deadline
        ):
            user_obj_id = session.get("user_obj_id")
            if user_obj_id is None:
                try:
                    user_obj_id = ObjectId(user_id)
                except (InvalidId, TypeError):
                    continue

            user = db.users.find_one({"_id": user_obj_id})
            if not user:
                continue

            emergency_id = trigger_emergency(
                db=db,
                user=user,
                source="inactivity",
                trigger_word="inactivity_timeout",
                transcript="No response to safety check within 5 minutes.",
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


async def _monitor_loop() -> None:
    global _monitor_running
    _monitor_running = True
    while _monitor_running:
        _process_inactivity_checks()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_safety_monitor() -> None:
    global _monitor_task
    if _monitor_task is None:
        _monitor_task = asyncio.create_task(_monitor_loop())


async def stop_safety_monitor() -> None:
    global _monitor_task, _monitor_running
    _monitor_running = False
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
    _monitor_task = None
