from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.core.security import decode_access_token
from app.db.mongo import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def _extract_token(authorization: str | None, oauth_token: str | None) -> str:
    if oauth_token:
        return oauth_token

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    value = authorization.strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    if value.lower().startswith("bearer "):
        token = value[7:].strip()
    else:
        token = value

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    return token


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Database = Depends(get_db),
) -> dict:
    parsed_token = _extract_token(authorization=authorization, oauth_token=token)
    payload = decode_access_token(parsed_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    try:
        user_id = ObjectId(payload["sub"])
    except (InvalidId, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc

    user = db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
