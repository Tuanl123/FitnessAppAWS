"""Shared JWT authentication dependency.

Provides get_current_user as a FastAPI Depends() callable that decodes
the JWT access token from the Authorization header and returns the user_id.
Used by both User Service and Metrics Service.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_bearer_scheme = HTTPBearer()

_jwt_secret: str | None = None
_jwt_algorithm: str = "HS256"


def configure(secret: str, algorithm: str = "HS256") -> None:
    """Set the JWT secret and algorithm. Called once at app startup."""
    global _jwt_secret, _jwt_algorithm
    _jwt_secret = secret
    _jwt_algorithm = algorithm


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> uuid.UUID:
    """Decode the access token and return the user_id (UUID).

    Raises 401 if the token is missing, expired, or malformed.
    """
    if _jwt_secret is None:
        raise RuntimeError("shared.auth not configured — call configure() at startup")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _jwt_secret, algorithms=[_jwt_algorithm])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not accepted")
        return uuid.UUID(sub)
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
