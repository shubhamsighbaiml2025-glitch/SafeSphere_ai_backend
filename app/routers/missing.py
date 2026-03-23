from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.missing import MissingPersonResponse, ReportMissingRequest, SeenReportRequest
from app.utils.serializers import serialize_document

router = APIRouter(tags=["Missing"])


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


@router.post("/report-missing", status_code=status.HTTP_201_CREATED)
@router.post("/missing", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def report_missing(
    payload: ReportMissingRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    doc = {
        "name": payload.name,
        "photo_url": payload.photo_url,
        "last_seen_location": payload.last_seen_location,
        "time": payload.time,
        "status": "MISSING",
        "reported_by": str(current_user["_id"]),
    }
    result = db.missing_persons.insert_one(doc)
    _create_notification(
        db=db,
        user_id=str(current_user["_id"]),
        notif_type="MISSING",
        title="Missing Report Created",
        message=f"Missing person report submitted for {payload.name}.",
    )
    return {"message": "Missing person reported", "person_id": str(result.inserted_id)}


@router.get("/missing-list", response_model=list[MissingPersonResponse])
@router.get("/missing", response_model=list[MissingPersonResponse], include_in_schema=False)
@router.get("/missing-people", response_model=list[MissingPersonResponse], include_in_schema=False)
def missing_list(
    current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)
) -> list[MissingPersonResponse]:
    _ = current_user
    records = db.missing_persons.find().sort("time", -1)
    response: list[MissingPersonResponse] = []
    for item in records:
        obj = serialize_document(item)
        response.append(
            MissingPersonResponse(
                id=obj["id"],
                name=obj["name"],
                photo_url=obj.get("photo_url"),
                last_seen_location=obj["last_seen_location"],
                time=obj["time"],
                status=obj["status"],
            )
        )
    return response


@router.post("/seen-report")
@router.post("/missing/seen-report", include_in_schema=False)
def seen_report(
    payload: SeenReportRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    try:
        person_id = ObjectId(payload.person_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid person_id"
        ) from exc

    person = db.missing_persons.find_one({"_id": person_id})
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Missing person not found"
        )

    db.sightings.insert_one(
        {
            "person_id": str(person["_id"]),
            "reporter_id": str(current_user["_id"]),
            "reporter_location": payload.reporter_location,
            "timestamp": datetime.now(timezone.utc),
        }
    )

    reporter_user_id = person.get("reported_by")
    if reporter_user_id:
        _create_notification(
            db=db,
            user_id=reporter_user_id,
            notif_type="SIGHTING",
            title="Sighting Reported",
            message=f"A sighting was reported for {person['name']}.",
        )
    return {"message": "Sighting report submitted"}
