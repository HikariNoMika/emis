"""TOTP (RFC 6238) using only the Python standard library.

No external dependency. Compatible with Google Authenticator, Authy, FreeOTP
and other authenticator apps via the otpauth:// URI.
"""

import base64
import hashlib
import hmac
import os
import struct
import time
import urllib.parse


def generate_secret(length=20):
    """Random base32 secret (no padding), 160 bits by default."""
    return base64.b32encode(os.urandom(length)).decode("ascii").rstrip("=")


def _decode_base32(secret):
    value = secret.strip().replace(" ", "").upper()
    return base64.b32decode(value + "=" * ((8 - len(value) % 8) % 8))


def _hotp(key, counter):
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return code % 1000000


def verify_code(secret, code, window=1, for_time=None):
    """Verify a 6-digit code, accepting ±window 30-second steps for clock drift."""
    if not secret or not code:
        return False
    code = str(code).strip()
    if not code.isdigit() or len(code) != 6:
        return False
    try:
        key = _decode_base32(secret)
    except Exception:
        return False
    counter = int((for_time or time.time()) // 30)
    for offset in range(-window, window + 1):
        if hmac.compare_digest(f"{_hotp(key, counter + offset):06d}", code):
            return True
    return False


def provisioning_uri(secret, account_name, issuer="EMIS"):
    """otpauth:// URI for authenticator apps."""
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    params = urllib.parse.urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    })
    return f"otpauth://totp/{label}?{params}"
