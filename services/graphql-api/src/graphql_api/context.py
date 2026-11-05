from dataclasses import replace

from strawberry import Info

from shared.auth import CurrentUser, Role, require_role
from shared.errors import DomainError, ErrorCode

from .auth_client import AuthClient
from .gateways import CatalogGateway


class RequestAuth:
    def __init__(
        self, authorization: str | None, auth: AuthClient, catalog: CatalogGateway
    ) -> None:
        self.authorization = authorization
        self.auth = auth
        self.catalog = catalog
        self._user: CurrentUser | None = None

    @property
    def access_token(self) -> str:
        if not self.authorization or not self.authorization.startswith("Bearer "):
            raise DomainError(ErrorCode.UNAUTHENTICATED, "Bearer token is required")
        token = self.authorization.removeprefix("Bearer ").strip()
        if not token:
            raise DomainError(ErrorCode.UNAUTHENTICATED, "Bearer token is required")
        return token

    async def current_user(self) -> CurrentUser:
        if self._user is None:
            user = await self.auth.authenticate(self.access_token)
            if user.role is Role.TEACHER:
                teacher = await self.catalog.get_teacher_by_user_id(user.user_id)
                if teacher is not None:
                    user = replace(user, teacher_id=teacher.id)
            self._user = user
        return self._user

    async def require_user(self, *roles: Role) -> CurrentUser:
        user = await self.current_user()
        return require_role(user, *roles) if roles else user


async def actor(info: Info, *roles: Role) -> CurrentUser:
    return await info.context["auth"].require_user(*roles)
