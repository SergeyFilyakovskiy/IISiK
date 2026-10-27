from uuid import UUID

import strawberry
from strawberry import Info

from identity_service.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RoleCode,
    StudentProfileInput,
)

from .bff import BffService
from .schema import Role, Student, User, map_student, map_user


@strawberry.type
class AuthPayload:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: User


@strawberry.input
class RegisterStudentProfileInput:
    education_level: str | None = None
    learning_goal: str | None = None
    timezone: str | None = None


@strawberry.input
class RegisterUserInput:
    email: str
    password: str
    full_name: str
    role: Role
    student_profile: RegisterStudentProfileInput | None = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class RefreshTokenInput:
    refresh_token: str


@strawberry.input
class LogoutInput:
    access_token: str
    refresh_token: str


@strawberry.input
class UpdateStudentProfileInput:
    user_id: UUID
    education_level: str | None = None
    learning_goal: str | None = None
    timezone: str | None = None


def bff(info: Info) -> BffService:
    return info.context["bff"]


def auth_payload(response) -> AuthPayload:
    return AuthPayload(
        access_token=response.access_token,
        refresh_token=response.refresh_token,
        token_type=response.token_type,
        expires_in=response.expires_in,
        user=map_user(response.user),
    )


@strawberry.type
class Mutation:
    @strawberry.field
    async def register_user(self, info: Info, input: RegisterUserInput) -> AuthPayload:
        response = await bff(info).register(
            RegisterRequest(
                email=input.email,
                password=input.password,
                full_name=input.full_name,
                role=RoleCode(input.role.value),
                student_profile=(
                    StudentProfileInput(
                        education_level=input.student_profile.education_level,
                        learning_goal=input.student_profile.learning_goal,
                        timezone=input.student_profile.timezone,
                    )
                    if input.student_profile
                    else None
                ),
            )
        )
        return auth_payload(response)

    @strawberry.field
    async def login_user(self, info: Info, input: LoginInput) -> AuthPayload:
        response = await bff(info).login(LoginRequest(email=input.email, password=input.password))
        return auth_payload(response)

    @strawberry.field
    async def refresh_token(self, info: Info, input: RefreshTokenInput) -> AuthPayload:
        response = await bff(info).refresh(RefreshRequest(refresh_token=input.refresh_token))
        return auth_payload(response)

    @strawberry.field
    async def logout(self, info: Info, input: LogoutInput) -> bool:
        await bff(info).logout(input.access_token, input.refresh_token)
        return True

    @strawberry.field
    async def update_student_profile(self, info: Info, input: UpdateStudentProfileInput) -> Student:
        student = await bff(info).update_student_profile(
            input.user_id,
            input.education_level,
            input.learning_goal,
            input.timezone,
        )
        return map_student(student)
