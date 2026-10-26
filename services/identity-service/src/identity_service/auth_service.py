from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from shared.database import Database

from .errors import ErrorCode, IdentityError
from .mappers import to_user_response
from .models import Role, Student, User
from .schemas import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, RoleCode
from .security import hash_password, verify_password
from .tokens import TokenManager


class AuthService:
    def __init__(self, database: Database, tokens: TokenManager) -> None:
        self.database = database
        self.tokens = tokens

    async def register(self, data: RegisterRequest) -> AuthResponse:
        async with self.database.session() as session:
            role = await session.scalar(select(Role).where(Role.code == data.role.value))
            if role is None:
                raise IdentityError(ErrorCode.INVALID_REGISTRATION, "Role is not configured")

            user = User(
                email=str(data.email).lower(),
                password_hash=hash_password(data.password),
                full_name=data.full_name,
                role=role,
            )
            student = None
            if data.role == RoleCode.STUDENT:
                profile = data.student_profile
                student = Student(
                    education_level=profile.education_level if profile else None,
                    learning_goal=profile.learning_goal if profile else None,
                    timezone=profile.timezone if profile else None,
                )
            user.student = student
            session.add(user)
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise IdentityError(
                    ErrorCode.EMAIL_EXISTS, "Email is already registered"
                ) from error
            await session.refresh(user, attribute_names=["status"])
            if student is not None:
                await session.refresh(student, attribute_names=["status"])

        tokens = await self.tokens.issue_pair(user.id)
        return AuthResponse(**tokens.__dict__, user=to_user_response(user))

    async def login(self, data: LoginRequest) -> AuthResponse:
        async with self.database.session() as session:
            user = await session.scalar(
                select(User)
                .where(User.email == str(data.email).lower())
                .options(selectinload(User.role), selectinload(User.student))
            )
        if user is None or not verify_password(data.password, user.password_hash):
            raise IdentityError(ErrorCode.INVALID_CREDENTIALS, "Invalid email or password")
        self.ensure_active(user)
        tokens = await self.tokens.issue_pair(user.id)
        return AuthResponse(**tokens.__dict__, user=to_user_response(user))

    async def refresh(self, data: RefreshRequest) -> AuthResponse:
        payload = self.tokens.decode(data.refresh_token, "refresh")
        user = await self.get_active_user(payload.subject)
        tokens = await self.tokens.rotate_refresh(data.refresh_token)
        return AuthResponse(**tokens.__dict__, user=to_user_response(user))

    async def logout(self, access_token: str, refresh_token: str) -> None:
        access = await self.tokens.validate_access(access_token)
        refresh = self.tokens.decode(refresh_token, "refresh")
        if access.subject != refresh.subject:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Tokens belong to different users")
        await self.tokens.blacklist_access(access)
        await self.tokens.revoke_refresh(refresh_token)

    async def get_user(self, access_token: str) -> User:
        payload = await self.tokens.validate_access(access_token)
        return await self.get_active_user(payload.subject)

    async def get_active_user(self, user_id: UUID) -> User:
        async with self.database.session() as session:
            user = await session.scalar(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.role), selectinload(User.student))
            )
        if user is None:
            raise IdentityError(ErrorCode.USER_NOT_FOUND, "User not found")
        self.ensure_active(user)
        return user

    @staticmethod
    def ensure_active(user: User) -> None:
        if user.status != "ACTIVE":
            raise IdentityError(ErrorCode.USER_INACTIVE, "User is inactive")
