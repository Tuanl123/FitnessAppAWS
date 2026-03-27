"""Authentication routes: register, login, refresh."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import RefreshToken, User
from app.schemas import (
    AccessTokenResponse,
    RefreshTokenRequest,
    RegisterResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

router = APIRouter(prefix="/auth")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Return (jwt_string, sha256_hash_of_jwt)."""
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    token = jwt.encode(
        {"sub": str(user_id), "type": "refresh", "jti": jti, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account and return tokens."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=_hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    await db.flush()

    access_token = _create_access_token(user.id)
    refresh_jwt, refresh_hash = _create_refresh_token(user.id)

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    ))
    await db.commit()

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        access_token=access_token,
        refresh_token=refresh_jwt,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email/password and return tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = _create_access_token(user.id)
    refresh_jwt, refresh_hash = _create_refresh_token(user.id)

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    ))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_jwt)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    incoming_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == incoming_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or invalid")

    await db.delete(stored)

    access_token = _create_access_token(stored.user_id)
    refresh_jwt, refresh_hash = _create_refresh_token(stored.user_id)

    db.add(RefreshToken(
        user_id=stored.user_id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    ))
    await db.commit()

    return AccessTokenResponse(access_token=access_token)
