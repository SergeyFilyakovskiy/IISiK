from enum import StrEnum


class ErrorCode(StrEnum):
    EMAIL_EXISTS = "email_exists"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    INVALID_REGISTRATION = "invalid_registration"
    USER_NOT_FOUND = "user_not_found"
    USER_INACTIVE = "user_inactive"


class IdentityError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
