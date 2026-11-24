"""Tests for TOTP, password policy and MFA login flow."""

import time

import pytest

from app.services import auth_service
from app.utils import totp
from app.schemas import validate_password_policy


def test_totp_code_roundtrip():
    secret = totp.generate_secret()
    counter = int(time.time() // 30)
    # Generate a code for the current step using the same internal function.
    key = totp._decode_base32(secret)
    code = f"{totp._hotp(key, counter):06d}"
    assert totp.verify_code(secret, code) is True
    assert totp.verify_code(secret, "000000") is False or code == "000000"


def test_password_policy():
    assert validate_password_policy("Str0ngPassword!") == "Str0ngPassword!"
    with pytest.raises(ValueError):
        validate_password_policy("short")
    with pytest.raises(ValueError):
        validate_password_policy("alllowercase1!")


def test_mfa_login_flow(app, client, auth_headers):
    """Enabling MFA makes login return a challenge, then a code returns tokens."""
    # Setup + enable using the current authenticated admin.
    from app.models import User
    from app.extensions import db

    admin = db.session.query(User).filter_by(username="admin").first()
    setup = auth_service.mfa_setup(admin)
    secret = setup["secret"]
    key = totp._decode_base32(secret)
    code = f"{totp._hotp(key, int(time.time() // 30)):06d}"
    result = auth_service.mfa_enable(admin, code)
    assert len(result["recovery_codes"]) == 8

    # Password step now returns a challenge instead of tokens.
    challenged = auth_service.authenticate("admin", "Secret123!")
    assert challenged.get("mfa_required") is True
    assert challenged.get("mfa_token")

    # Completing with a valid TOTP code returns tokens.
    tokens = auth_service.mfa_verify(challenged["mfa_token"], code)
    assert tokens["access_token"]

    # Clean up so other tests are unaffected.
    auth_service.mfa_disable(admin, "Secret123!", code)
