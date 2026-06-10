from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.config import settings
from backend.core.security import create_access_token, hash_password, verify_password
from backend.models.user import User
from backend.schemas.user import UserLoginRequest, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    # Production serves frontend (Netlify) and API (Railway) on different
    # sites, so the cookie needs SameSite=None + Secure to flow on fetch.
    # Local dev runs over plain http where Secure cookies are dropped, so
    # DEBUG mode falls back to SameSite=Lax without Secure (same-host setup,
    # see DECISIONS.md D14/D16).
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax" if settings.DEBUG else "none",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegisterRequest, db: Session = Depends(get_db)) -> User:
    try:
        existing = db.execute(
            select(User).where(User.email == body.email)
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            company_name=body.company_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed"
        ) from exc


@router.post("/login", response_model=UserResponse)
def login(
    body: UserLoginRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    try:
        user = db.execute(
            select(User).where(User.email == body.email)
        ).scalar_one_or_none()
        if user is None or not verify_password(body.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        _set_auth_cookie(response, create_access_token(user.user_id))
        return user
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        ) from exc


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response) -> dict:
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return {"status": "logged_out"}
