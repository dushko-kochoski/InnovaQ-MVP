from typing import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.core.security import decode_access_token
from backend.database.session import SessionLocal
from backend.models.user import User


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    if token is None:
        raise credentials_error
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user
