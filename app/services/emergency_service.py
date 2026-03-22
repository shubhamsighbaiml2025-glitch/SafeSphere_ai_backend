from datetime import datetime, timezone

from pymongo.database import Database


def create_notification(
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


def _resolve_location(db: Database, user_id: str) -> dict:
    latest_location = db.location_logs.find_one(
        {"user_id": user_id},
        sort=[("time", -1)],
    )
    if latest_location:
        return {
            "lat": float(latest_location.get("latitude", 0.0)),
            "long": float(latest_location.get("longitude", 0.0)),
        }
    return {"lat": 0.0, "long": 0.0}


def trigger_emergency(
    db: Database,
    user: dict,
    source: str,
    trigger_word: str | None = None,
    transcript: str | None = None,
    location: dict | None = None,
    ai_processed_locally: bool = True,
) -> str:
    user_id = str(user["_id"])
    effective_location = location or _resolve_location(db, user_id)

    emergency_doc = {
        "user_id": user_id,
        "location": {
            "lat": float(effective_location["lat"]),
            "long": float(effective_location["long"]),
        },
        "source": source,
        "trigger_word": trigger_word,
        "transcript": transcript,
        "ai_processed_locally": ai_processed_locally,
        "status": "ACTIVE",
        "timestamp": datetime.now(timezone.utc),
    }
    result = db.emergencies.insert_one(emergency_doc)

    create_notification(
        db=db,
        user_id=user_id,
        notif_type="EMERGENCY",
        title="SOS Activated",
        message=f"Emergency alert triggered via {source}.",
    )
    db.notifications.insert_one(
        {
            "user_id": "ADMIN",
            "type": "EMERGENCY_ADMIN",
            "title": "Emergency Triggered",
            "message": (
                f"User {user_id} triggered SOS via {source}. "
                f"Location: {effective_location['lat']}, {effective_location['long']}"
            ),
            "timestamp": datetime.now(timezone.utc),
            "status": "UNREAD",
        }
    )

    for contact in user.get("emergency_contacts", []):
        db.notifications.insert_one(
            {
                "user_id": user_id,
                "type": "CONTACT_ALERT",
                "title": "Emergency Contact Alert",
                "message": (
                    f"Alert sent to emergency contact {contact}. "
                    f"Live tracking started for this SOS."
                ),
                "timestamp": datetime.now(timezone.utc),
                "status": "UNREAD",
                "contact": contact,
            }
        )

    return str(result.inserted_id)
