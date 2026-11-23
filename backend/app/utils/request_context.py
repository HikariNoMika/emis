"""
Request metadata available to services without a web-framework import.

FastAPI middleware fills these values for each request. Services (audit logging,
login history) read them from here instead of depending on Flask's `request`.
"""

import contextvars

_request_info = contextvars.ContextVar("emis_request_info", default={})


def set_request_info(ip_address=None, user_agent=None, user_id=None):
    _request_info.set(
        {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "user_id": user_id,
        }
    )


def get_request_info():
    return _request_info.get() or {}


def set_current_user_id(user_id):
    info = dict(get_request_info())
    info["user_id"] = user_id
    _request_info.set(info)
