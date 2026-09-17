"""Auth service: hashlib PBKDF2 hashing, PyJWT access, opaque refresh."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.exceptions import EmailAlreadyRegistered, InvalidCredentials, InvalidRefreshToken, UserInactive
from app.models.user import RefreshToken, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 210_000).hex()
    return f"pbkdf2_sha256$210000${salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, iters, salt, digest = hashed.split("$")
        assert algo == "pbkdf2_sha256"
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters)).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID, *, secret: str, minutes: int) -> str:
    now = _utcnow()
    payload = {"sub": str(user_id), "type": "access", "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=minutes)).timestamp()), "jti": uuid.uuid4().hex}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, *, secret: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "exp", "type"]})
    except jwt.ExpiredSignatureError as exc:
        raise InvalidCredentials("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidCredentials("Invalid token") from exc
    if payload.get("type") != "access":
        raise InvalidCredentials("Invalid token type")
    return uuid.UUID(str(payload["sub"]))


def register_user(db: Session, *, email: str, full_name: str, password: str) -> User:
    existing = db.execute(select(User).where(User.email == email.strip().lower()).limit(1)).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyRegistered("Email already registered")
    user = User(email=email.strip().lower(), full_name=full_name.strip(), hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str, secret: str, access_minutes: int, refresh_days: int) -> tuple[User, str, str]:
    user = db.execute(select(User).where(User.email == email.strip().lower()).limit(1)).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentials("Invalid email or password")
    if not user.is_active:
        raise UserInactive("User is inactive")
    access = create_access_token(user.id, secret=secret, minutes=access_minutes)
    raw_refresh = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user.id, token_hash=_hash_token(raw_refresh), jti=uuid.uuid4().hex, expires_at=_utcnow() + timedelta(days=refresh_days)))
    db.commit()
    return user, access, raw_refresh


def rotate_refresh(db: Session, *, raw_token: str, secret: str, access_minutes: int, refresh_days: int) -> tuple[User, str, str]:
    row = db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token)).limit(1)).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise InvalidRefreshToken("Invalid refresh token")
    expires = row.expires_at if row.expires_at.tzinfo is not None else row.expires_at.replace(tzinfo=timezone.utc)
    if expires <= _utcnow():
        raise InvalidRefreshToken("Invalid refresh token")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UserInactive("User is inactive")
    row.revoked_at = _utcnow()
    new_jti = uuid.uuid4().hex
    row.replaced_by_jti = new_jti
    raw_new = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user.id, token_hash=_hash_token(raw_new), jti=new_jti, expires_at=_utcnow() + timedelta(days=refresh_days)))
    db.commit()
    access = create_access_token(user.id, secret=secret, minutes=access_minutes)
    return user, access, raw_new


def revoke_refresh(db: Session, *, raw_token: str) -> None:
    row = db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token)).limit(1)).scalar_one_or_none()
    if row is None:
        return
    row.revoked_at = _utcnow()
    db.add(row)
    db.commit()
