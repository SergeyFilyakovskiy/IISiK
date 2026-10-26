from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator


class RoleCode(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"


class StudentProfileInput(BaseModel):
    education_level: str | None = Field(default=None, max_length=100)
    learning_goal: str | None = None
    timezone: str | None = Field(default=None, max_length=64)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    role: RoleCode
    student_profile: StudentProfileInput | None = None

    @model_validator(mode="after")
    def validate_student_profile(self) -> RegisterRequest:
        if self.role != RoleCode.STUDENT and self.student_profile is not None:
            raise ValueError("student_profile is allowed only for students")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class StudentProfileResponse(BaseModel):
    id: UUID
    education_level: str | None
    learning_goal: str | None
    timezone: str | None
    status: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    status: str
    student: StudentProfileResponse | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class HealthResponse(BaseModel):
    status: str
