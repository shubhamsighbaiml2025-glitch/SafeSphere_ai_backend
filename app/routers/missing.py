from datetime import datetime, timezone
from pathlib import Path
import secrets

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.missing import (
    MarkFoundRequest,
    MissingPersonResponse,
    ReportMissingRequest,
    SeenReportRequest,
)
from app.utils.serializers import serialize_document

router = APIRouter(tags=["Missing"])
UPLOAD_DIR = Path("app/static/uploads/missing")
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def _save_missing_photo(photo: UploadFile, request: Request) -> str:
    if photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Use jpg, png, webp, or gif.",
        )

    content = await photo.read()
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is too large. Maximum size is 5MB.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ALLOWED_IMAGE_TYPES[photo.content_type]
    file_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(8)}{suffix}"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(content)

    return f"{request.base_url}static/uploads/missing/{file_name}"


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
async def report_missing(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    payload: ReportMissingRequest | None = Body(default=None),
    name: str | None = Form(default=None),
    last_seen_location: str | None = Form(default=None),
    time: datetime | None = Form(default=None),
    photo_url: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    if payload is not None:
        resolved_name = payload.name
        resolved_photo_url = payload.photo_url
        resolved_last_seen_location = payload.last_seen_location
        resolved_time = payload.time
    else:
        if not name or not last_seen_location or not time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "For multipart requests, required fields are: "
                    "name, last_seen_location, and time."
                ),
            )

        resolved_name = name
        resolved_last_seen_location = last_seen_location
        resolved_time = time
        resolved_photo_url = photo_url

    upload = photo or image or file
    if upload is not None:
        resolved_photo_url = await _save_missing_photo(upload, request)

    doc = {
        "name": resolved_name,
        "photo_url": resolved_photo_url,
        "last_seen_location": resolved_last_seen_location,
        "time": resolved_time,
        "status": "MISSING",
        "reported_by": str(current_user["_id"]),
    }
    result = db.missing_persons.insert_one(doc)
    _create_notification(
        db=db,
        user_id=str(current_user["_id"]),
        notif_type="MISSING",
        title="Missing Report Created",
        message=f"Missing person report submitted for {resolved_name}.",
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


@router.post("/missing/mark-found")
@router.post("/mark-found", include_in_schema=False)
def mark_missing_person_found(
    payload: MarkFoundRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    _ = current_user
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

    db.missing_persons.update_one(
        {"_id": person_id},
        {"$set": {"status": "FOUND"}},
    )

    reporter_user_id = person.get("reported_by")
    if reporter_user_id:
        _create_notification(
            db=db,
            user_id=reporter_user_id,
            notif_type="MISSING_FOUND",
            title="Missing Person Marked Found",
            message=f"{person['name']} has been marked as FOUND.",
        )
    return {"message": "Missing person status updated to FOUND"}
