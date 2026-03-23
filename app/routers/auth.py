from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongo import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.utils.serializers import serialize_document

router = APIRouter(tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@router.post("/auth/register", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def register(payload: RegisterRequest, db: Database = Depends(get_db)) -> dict:
    existing_user = db.users.find_one({"email": payload.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user_doc = {
        "name": payload.name,
        "email": payload.email.lower(),
        "password_hash": password_hash,
        "emergency_contacts": payload.emergency_contacts,
        "created_at": datetime.now(timezone.utc),
    }
    result = db.users.insert_one(user_doc)

    return {"message": "User created successfully", "user_id": str(result.inserted_id)}


@router.post("/login", response_model=TokenResponse)
@router.post("/auth/login", response_model=TokenResponse, include_in_schema=False)
def login(payload: LoginRequest, db: Database = Depends(get_db)) -> TokenResponse:
    user = db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=str(user["_id"]))
    return TokenResponse(access_token=token)


@router.get("/profile", response_model=UserProfileResponse)
@router.get("/auth/profile", response_model=UserProfileResponse, include_in_schema=False)
def get_profile(current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    user = serialize_document(current_user)
    return UserProfileResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        emergency_contacts=user.get("emergency_contacts", []),
        created_at=user["created_at"],
    )
