"""Authentication business logic (FastAPI-compatible)."""

import os
from datetime import datetime, timezone

from app.extensions import db
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas import UserSchema
from app.utils.security import (
    create_access_token,
    create_mfa_challenge,
    create_refresh_token,
    hash_password,
    revoke_token,
    verify_password,
)

from .audit_service import log_action
from .exceptions import AccountInactiveError, AuthenticationError, ValidationAppError


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

    # If MFA is enabled, the password step alone is not enough. Return a
    # short-lived challenge that must be exchanged for a code in /mfa/verify.
    if user.mfa_enabled:
        return {
            "mfa_required": True,
            "mfa_token": create_mfa_challenge(user.id),
        }

    return {
        "access_token": create_access_token(user.id, claims),
        "refresh_token": create_refresh_token(user.id, claims),
        "token_type": "Bearer",
        "user": UserSchema.model_validate(user).model_dump(),
    }


def mfa_setup(user):
    """Generate a new TOTP secret and otpauth URI. Not active until enabled."""
    from app.utils import totp

    secret = totp.generate_secret()
    # Store as pending on the user; enabling requires a valid code from it.
    user.mfa_secret = secret
    db.session.commit()
    return {
        "secret": secret,
        "otpauth_uri": totp.provisioning_uri(secret, user.username),
    }


def mfa_enable(user, code):
    """Verify a code from the new secret, then activate MFA and issue codes."""
    from app.utils import totp

    if not user.mfa_secret:
        raise ValidationAppError("Start MFA setup first.")
    if not totp.verify_code(user.mfa_secret, code):
        raise AuthenticationError("Invalid authenticator code.")
    user.mfa_enabled = True
    # 8 recovery codes, shown once, stored as hashes and single-use.
    from app.utils.security import hash_password

    codes = [f"{os.urandom(4).hex()}" for _ in range(8)]
    user.mfa_recovery_codes = [hash_password(code) for code in codes]
    log_action("MFA_ENABLED", "auth", record_identifier=user.id, user_id=user.id, commit=False)
    db.session.commit()
    return {"recovery_codes": codes}


def mfa_disable(user, password, code):
    """Require password + a current code to turn MFA off."""
    from app.utils import totp

    if not verify_password(user.password_hash, password):
        raise AuthenticationError("Password is incorrect.")
    if not totp.verify_code(user.mfa_secret, code):
        raise AuthenticationError("Invalid authenticator code.")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_recovery_codes = None
    log_action("MFA_DISABLED", "auth", record_identifier=user.id, user_id=user.id, commit=False)
    db.session.commit()


def mfa_verify(mfa_token, code):
    """Complete login after the MFA challenge. Accepts TOTP or a recovery code."""
    from app.utils import totp
    from app.utils.security import decode_token, verify_password

    payload = decode_token(mfa_token, "mfa")
    user = db.session.get(User, int(payload["sub"]))
    if user is None or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise AuthenticationError("MFA is not active for this account.")

    verified = totp.verify_code(user.mfa_secret, code)
    used_recovery = False
    if not verified and user.mfa_recovery_codes:
        for index, hashed in enumerate(user.mfa_recovery_codes):
            if verify_password(hashed, str(code).strip()):
                user.mfa_recovery_codes.pop(index)
                used_recovery = True
                verified = True
                break

    if not verified:
        raise AuthenticationError("Invalid authenticator or recovery code.")

    user.last_login_at = datetime.now(timezone.utc)
    UserRepository.record_login_event(user.id, "LOGIN")
    log_action("MFA_LOGIN", "auth", record_identifier=user.id, user_id=user.id, commit=False)
    db.session.commit()

    claims = {"role": user.role, "username": user.username}
    return {
        "access_token": create_access_token(user.id, claims),
        "refresh_token": create_refresh_token(user.id, claims),
        "token_type": "Bearer",
        "user": UserSchema.model_validate(user).model_dump(),
        "recovery_code_used": used_recovery,
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
