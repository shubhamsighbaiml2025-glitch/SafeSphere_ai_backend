from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.core.security import decode_access_token
from app.db.mongo import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)
) -> dict:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.users.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

