"""Authentication routes: /api/v1/auth/*."""

import time

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import (
    ChangePasswordSchema,
    LoginSchema,
    MFACodeSchema,
    MFADisableSchema,
    MFAVerifySchema,
    UserProfileUpdateSchema,
)
from app.services import auth_service, user_management_service
from app.utils.responses import ok
from app.utils.security import (
    create_access_token,
    get_current_user,
    get_refresh_claims,
    get_token_payload,
)

auth_bp = APIRouter()

# Simple in-memory rate limit for login attempts (Redis is recommended in production).
_login_attempts = {}


def _check_login_rate(identifier):
    from app.config import get_settings

    if get_settings().TESTING:
        return  # tests log in many times quickly
    now = time.time()
    attempts = [stamp for stamp in _login_attempts.get(identifier, []) if now - stamp < 60]
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    attempts.append(now)
    _login_attempts[identifier] = attempts


@auth_bp.post("/login")
def login(payload: LoginSchema):
    _check_login_rate(payload.identifier)
    data = auth_service.authenticate(payload.identifier, payload.password)
    return ok(data=data, message="Login successful.")


# ---- Multi-factor authentication --------------------------------------------
@auth_bp.post("/mfa/setup")
def mfa_setup(user=Depends(get_current_user)):
    """Begin enrolment: returns a secret + otpauth URI (not active yet)."""
    return ok(data=auth_service.mfa_setup(user), message="Scan the code with your authenticator app.")


@auth_bp.post("/mfa/enable")
def mfa_enable(payload: MFACodeSchema, user=Depends(get_current_user)):
    """Activate MFA with a code from the new secret; returns recovery codes."""
    return ok(data=auth_service.mfa_enable(user, payload.code), message="MFA enabled.")


@auth_bp.post("/mfa/disable")
def mfa_disable(payload: MFADisableSchema, user=Depends(get_current_user)):
    """Turn off MFA (requires password and a current code)."""
    auth_service.mfa_disable(user, payload.password, payload.code)
    return ok(message="MFA disabled.")


@auth_bp.post("/mfa/verify")
def mfa_verify(payload: MFAVerifySchema):
    """Complete a login that returned mfa_required."""
    return ok(data=auth_service.mfa_verify(payload.mfa_token, payload.code), message="Login successful.")


@auth_bp.post("/logout")
def logout(claims: dict = Depends(get_token_payload), user=Depends(get_current_user)):
    auth_service.logout(claims.get("jti"), claims.get("exp"), user.id)
    return ok(message="Logged out successfully.")


@auth_bp.get("/me")
def me(user=Depends(get_current_user)):
    return ok(data=auth_service.profile_dict(user))


@auth_bp.post("/refresh")
def refresh(claims: dict = Depends(get_refresh_claims)):
    """Exchange a valid refresh token for a new access token."""
    token = create_access_token(
        int(claims["sub"]),
        {"role": claims.get("role"), "username": claims.get("username")},
    )
    return ok(data={"access_token": token})


@auth_bp.post("/change-password")
def change_password(payload: ChangePasswordSchema, user=Depends(get_current_user)):
    result = auth_service.change_password(
        user, payload.current_password, payload.new_password
    )
    data = result.get("mfa_enrolment") if isinstance(result, dict) else None
    return ok(
        data=data,
        message="Password changed successfully." + (" MFA setup required." if data else ""),
    )


@auth_bp.put("/profile")
def update_profile(payload: UserProfileUpdateSchema, user=Depends(get_current_user)):
    """Any authenticated user can edit their own name and email."""
    updated = user_management_service.update_own_profile(
        user, payload.full_name, payload.email, user.id
    )
    return ok(data=auth_service.profile_dict(updated), message="Profile updated.")
