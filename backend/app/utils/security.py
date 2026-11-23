"""
Authentication helpers: password hashing, JWT creation/validation dependencies
and the logout blocklist.

Access and refresh tokens are signed with PyJWT. The dependencies below replace
Flask-JWT-Extended while keeping the same /api/v1/auth endpoints.
"""

import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import get_settings

from .request_context import set_current_user_id

bearer_scheme = HTTPBearer(auto_error=False)

# jti -> expiry. Process-local blocklist; use Redis in multi-worker production.
_TOKEN_BLOCKLIST = {}


def hash_password(plain_password):
    return generate_password_hash(plain_password)


def verify_password(stored_hash, plain_password):
    if not stored_hash:
        return False
    return check_password_hash(stored_hash, plain_password)


def revoke_token(jti, expires_at=None):
    if jti:
        _TOKEN_BLOCKLIST[jti] = expires_at


def is_token_revoked(jti):
    _cleanup_blocklist()
    return jti in _TOKEN_BLOCKLIST


def _cleanup_blocklist():
    now = datetime.now(timezone.utc)
    for jti, expiry in list(_TOKEN_BLOCKLIST.items()):
        if expiry and expiry <= now:
            _TOKEN_BLOCKLIST.pop(jti, None)


def _create_token(user_id, token_type, claims, expires):
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        "jti": uuid.uuid4().hex,
        **claims,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id, claims=None):
    return _create_token(
        user_id, "access", claims or {}, get_settings().JWT_ACCESS_TOKEN_EXPIRES
    )


def create_refresh_token(user_id, claims=None):
    return _create_token(
        user_id, "refresh", claims or {}, get_settings().JWT_REFRESH_TOKEN_EXPIRES
    )


def decode_token(token, expected_type="access"):
    """Decode and validate a token. Raises HTTPException 401 on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Wrong token type.")
    if is_token_revoked(payload.get("jti")):
        raise HTTPException(status_code=401, detail="Token has been revoked.")
    return payload


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """FastAPI dependency: returns the authenticated administrator."""
    from app.models import User

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_token(credentials.credentials, "access")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject.")

    from app.extensions import db

    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive or missing.")
    set_current_user_id(user.id)
    return user


def get_token_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Dependency that returns raw claims from an access token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return decode_token(credentials.credentials, "access")


def get_refresh_claims(request: Request):
    """Dependency that validates a refresh token sent as a Bearer header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return decode_token(header.split(" ", 1)[1], "refresh")
