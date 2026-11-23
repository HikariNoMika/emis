"""Authentication business logic (FastAPI-compatible)."""

from datetime import datetime, timezone

from app.extensions import db
from app.repositories.user_repository import UserRepository
from app.schemas import UserSchema
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_token,
    verify_password,
)

from .audit_service import log_action
from .exceptions import AccountInactiveError, AuthenticationError


def authenticate(identifier, password):
    """Validate credentials and return tokens plus the user profile."""
    user = UserRepository.find_by_identifier(identifier)
    if user is None or not verify_password(user.password_hash, password):
        raise AuthenticationError("Invalid username or password.")
    if not user.is_active:
        raise AccountInactiveError(
            "This account is inactive. Contact the system administrator."
        )

    user.last_login_at = datetime.now(timezone.utc)
    UserRepository.record_login_event(user.id, "LOGIN")
    log_action("LOGIN", "auth", record_identifier=user.id, user_id=user.id, commit=False)
    db.session.commit()

    claims = {"role": user.role, "username": user.username}
    return {
        "access_token": create_access_token(user.id, claims),
        "refresh_token": create_refresh_token(user.id, claims),
        "token_type": "Bearer",
        "user": UserSchema.model_validate(user).model_dump(),
    }


def logout(jti, expires_at_timestamp, user_id):
    """Revoke the current access token and record the logout event."""
    expiry = None
    if expires_at_timestamp:
        expiry = datetime.fromtimestamp(float(expires_at_timestamp), tz=timezone.utc)
    revoke_token(jti, expiry)
    UserRepository.record_login_event(user_id, "LOGOUT")
    log_action("LOGOUT", "auth", record_identifier=user_id, user_id=user_id)


def change_password(user, current_password, new_password):
    if not verify_password(user.password_hash, current_password):
        raise AuthenticationError("Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    log_action(
        "PASSWORD_CHANGED", "auth", record_identifier=user.id,
        user_id=user.id, commit=False,
    )
    db.session.commit()
    return user


def profile_dict(user):
    return UserSchema.model_validate(user).model_dump()
