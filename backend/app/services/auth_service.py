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


def mfa_setup(user, send_mail=True):
    """Generate a TOTP secret, QR code and otpauth URI, and email the secret.

    Not active until a valid code is submitted via mfa_enable.
    """
    from app.utils import totp
    from app.utils.email import send_email

    secret = totp.generate_secret()
    uri = totp.provisioning_uri(secret, user.username)
    user.mfa_secret = secret
    db.session.commit()

    emailed = False
    if send_mail:
        emailed = send_email(
            user.email,
            "EMIS - Authenticator setup code",
            (
                f"Hello {user.full_name},\n\n"
                "An authenticator app was set up for your EMIS account.\n"
                "Scan the QR code shown on screen, or enter this secret manually:\n\n"
                f"  {secret}\n\n"
                "If you did not request this, contact your administrator immediately.\n"
            ),
        )
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_data_uri": totp.qr_data_uri(uri),
        "email_sent": emailed,
    }


def _activate_mfa(user):
    """Activate MFA with the pending secret and issue one-time recovery codes."""
    from app.utils.security import hash_password

    user.mfa_enabled = True
    codes = [f"{os.urandom(4).hex()}" for _ in range(8)]
    user.mfa_recovery_codes = [hash_password(code) for code in codes]
    log_action("MFA_ENABLED", "auth", record_identifier=user.id, user_id=user.id, commit=False)
    db.session.commit()
    return codes


def mfa_enable(user, code):
    """Verify a code from the new secret, then activate MFA and issue codes."""
    from app.utils import totp

    if not user.mfa_secret:
        raise ValidationAppError("Start MFA setup first.")
    if not totp.verify_code(user.mfa_secret, code):
        raise AuthenticationError("Invalid authenticator code.")
    return {"recovery_codes": _activate_mfa(user)}


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
    was_forced = user.must_change_password
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    log_action(
        "PASSWORD_CHANGED", "auth", record_identifier=user.id,
        user_id=user.id, commit=False,
    )
    db.session.commit()
    # On a forced first-login change, optionally auto-enrol MFA and email the
    # secret. Controlled by an admin-editable setting (off by default in testing).
    if was_forced and not user.mfa_enabled and _enforce_first_login_mfa():
        setup = mfa_setup(user, send_mail=True)
        codes = _activate_mfa(user)
        return {
            "password_changed": True,
            "mfa_enrolment": {**setup, "recovery_codes": codes},
        }
    return {"password_changed": True}


def _enforce_first_login_mfa():
    """Read the admin toggle; safe default False while the feature is in testing."""
    from app.models import SystemSetting

    setting = SystemSetting.query.filter_by(key="enforce_mfa_on_first_login").first()
    if setting is None:
        return False
    value = setting.value
    if isinstance(value, dict):
        value = value.get("enabled", False)
    return str(value).lower() in ("true", "1", "yes") if not isinstance(value, bool) else value


def profile_dict(user):
    return UserSchema.model_validate(user).model_dump()
