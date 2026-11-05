from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from shared.errors import DomainError, ErrorCode

USER_ID_METADATA_KEY = "user-id"
USER_ROLE_METADATA_KEY = "user-role"
STUDENT_ID_METADATA_KEY = "student-id"
TEACHER_ID_METADATA_KEY = "teacher-id"


class Role(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


@dataclass(frozen=True, slots=True)
class CurrentUser:
    user_id: UUID
    role: Role
    student_id: UUID | None = None
    teacher_id: UUID | None = None


def require_authenticated(user: CurrentUser | None) -> CurrentUser:
    if user is None:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "Authentication is required")
    return user


def require_role(
    user: CurrentUser | None,
    *roles: Role,
    admin_override: bool = False,
) -> CurrentUser:
    principal = require_authenticated(user)
    if not roles:
        raise ValueError("At least one role is required")
    if principal.role in roles or (admin_override and principal.role is Role.ADMIN):
        return principal
    raise DomainError(ErrorCode.FORBIDDEN, "Insufficient role permissions")


def require_user_owner(user: CurrentUser | None, user_id: UUID) -> CurrentUser:
    principal = require_authenticated(user)
    if principal.role is Role.ADMIN or principal.user_id == user_id:
        return principal
    raise DomainError(ErrorCode.FORBIDDEN, "Access to another user's resource is forbidden")


def require_student_owner(user: CurrentUser | None, student_id: UUID) -> CurrentUser:
    principal = require_authenticated(user)
    if principal.role is Role.ADMIN or principal.student_id == student_id:
        return principal
    raise DomainError(ErrorCode.FORBIDDEN, "Access to another student's resource is forbidden")


def require_teacher_owner(user: CurrentUser | None, teacher_id: UUID) -> CurrentUser:
    principal = require_authenticated(user)
    if principal.role is Role.ADMIN or principal.teacher_id == teacher_id:
        return principal
    raise DomainError(ErrorCode.FORBIDDEN, "Access to another teacher's resource is forbidden")


def principal_to_metadata(user: CurrentUser) -> dict[str, str]:
    metadata = {
        USER_ID_METADATA_KEY: str(user.user_id),
        USER_ROLE_METADATA_KEY: user.role.value,
    }
    if user.student_id is not None:
        metadata[STUDENT_ID_METADATA_KEY] = str(user.student_id)
    if user.teacher_id is not None:
        metadata[TEACHER_ID_METADATA_KEY] = str(user.teacher_id)
    return metadata


def principal_from_metadata(metadata: Mapping[str, str | None]) -> CurrentUser:
    try:
        user_id = UUID(metadata[USER_ID_METADATA_KEY] or "")
        role = Role(metadata[USER_ROLE_METADATA_KEY] or "")
        student_id = _optional_uuid(metadata.get(STUDENT_ID_METADATA_KEY))
        teacher_id = _optional_uuid(metadata.get(TEACHER_ID_METADATA_KEY))
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "Invalid principal metadata") from error
    return CurrentUser(
        user_id=user_id,
        role=role,
        student_id=student_id,
        teacher_id=teacher_id,
    )


def _optional_uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None
