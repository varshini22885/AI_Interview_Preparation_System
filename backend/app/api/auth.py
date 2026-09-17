"""Auth routes: thin wrappers over app.auth.service."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_request_id, rate_limit_guard
from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserResponse
from app.core.config import get_settings
from app.db.base import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "interviews_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=(settings.APP_ENV == "production"),
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/v1/auth")


@router.post("/register", response_model=UserResponse, status_code=201, summary="Register account")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db), _rid: str = Depends(get_request_id)):
    from app.auth.service import register_user

    rate_limit_guard(request, "auth")
    user = register_user(db, email=str(payload.email), full_name=payload.full_name, password=payload.password)
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, created_at=user.created_at)


@router.post("/login", response_model=TokenPair, summary="Login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db), _rid: str = Depends(get_request_id)):
    from app.auth.service import authenticate

    rate_limit_guard(request, "auth")
    settings = get_settings()
    user, access, refresh = authenticate(db, email=str(payload.email), password=payload.password, secret=settings.SECRET_KEY, access_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES, refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    _set_refresh_cookie(response, refresh)
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
def refresh(payload: RefreshRequest | None = None, request: Request = None, response: Response = None, db: Session = Depends(get_db), _rid: str = Depends(get_request_id)):
    from app.auth.service import rotate_refresh

    rate_limit_guard(request, "auth")
    settings = get_settings()
    raw = payload.refresh_token if payload is not None and payload.refresh_token else request.cookies.get(REFRESH_COOKIE)
    if not raw:
        from app.auth.exceptions import InvalidRefreshToken

        raise InvalidRefreshToken("Missing refresh token")
    _, access, new_refresh = rotate_refresh(db, raw_token=raw, secret=settings.SECRET_KEY, access_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES, refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    _set_refresh_cookie(response, new_refresh)
    return TokenPair(access_token=access, refresh_token=new_refresh, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout", status_code=204, summary="Revoke refresh token")
def logout(payload: RefreshRequest | None = None, request: Request = None, response: Response = None, db: Session = Depends(get_db), _rid: str = Depends(get_request_id)):
    from app.auth.service import revoke_refresh

    rate_limit_guard(request, "auth")
    raw = payload.refresh_token if payload is not None and payload.refresh_token else request.cookies.get(REFRESH_COOKIE)
    if raw:
        revoke_refresh(db, raw_token=raw)
    _clear_refresh_cookie(response)
    return None


@router.get("/me", response_model=UserResponse, summary="Current user")
def me(user=Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, created_at=user.created_at)
