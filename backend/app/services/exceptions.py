"""Application-level exceptions that map cleanly to HTTP responses."""


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message, status_code=None, errors=None, code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.errors = errors


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTH_FAILED"


class AccountInactiveError(AppError):
    status_code = 403
    code = "ACCOUNT_INACTIVE"


class ValidationAppError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
