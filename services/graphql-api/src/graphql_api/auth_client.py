from dataclasses import asdict
from uuid import UUID

import httpx

from shared.auth import CurrentUser, Role
from shared.errors import DomainError, ErrorCode

from .dto import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, UserDTO


class AuthClient:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout))

    async def close(self) -> None:
        await self.client.aclose()

    async def register(self, data: RegisterRequest) -> AuthResponse:
        payload = {
            "email": data.email,
            "password": data.password,
            "full_name": data.full_name,
            "role": data.role,
            "student_profile": (
                {
                    key: value
                    for key, value in asdict(data.student_profile).items()
                    if value is not None
                }
                if data.student_profile
                else None
            ),
        }
        return self._auth_response(await self._post("/api/v1/auth/register", payload))

    async def login(self, data: LoginRequest) -> AuthResponse:
        return self._auth_response(
            await self._post("/api/v1/auth/login", {"email": data.email, "password": data.password})
        )

    async def refresh(self, data: RefreshRequest) -> AuthResponse:
        return self._auth_response(
            await self._post("/api/v1/auth/refresh", {"refresh_token": data.refresh_token})
        )

    async def logout(self, access_token: str, refresh_token: str) -> None:
        await self._request(
            "POST",
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def authenticate(self, access_token: str) -> CurrentUser:
        data = await self._request(
            "GET", "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        student = data.get("student")
        return CurrentUser(
            user_id=UUID(data["id"]),
            role=Role(data["role"]),
            student_id=UUID(student["id"]) if student else None,
        )

    async def _post(self, path: str, payload: dict) -> dict:
        return await self._request("POST", path, json=payload)

    async def _request(self, method: str, path: str, **kwargs):
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise DomainError(ErrorCode.TIMEOUT, "Auth Service timed out") from error
        except httpx.HTTPError as error:
            raise DomainError(ErrorCode.UNAVAILABLE, "Auth Service is unavailable") from error
        if response.status_code >= 400:
            if response.status_code == 401:
                code = ErrorCode.UNAUTHENTICATED
            elif response.status_code == 403:
                code = ErrorCode.FORBIDDEN
            elif response.status_code == 404:
                code = ErrorCode.NOT_FOUND
            elif response.status_code == 409:
                code = ErrorCode.CONFLICT
            elif response.status_code in {400, 422}:
                code = ErrorCode.VALIDATION_ERROR
            else:
                code = ErrorCode.UNAVAILABLE
            raise DomainError(code, response.json().get("detail", "Auth Service request failed"))
        if response.status_code == 204:
            return {}
        return response.json()

    @staticmethod
    def _user(data: dict) -> UserDTO:
        from .dto import StudentDTO

        student = data.get("student")
        return UserDTO(
            id=UUID(data["id"]),
            email=data["email"],
            full_name=data["full_name"],
            role=data["role"],
            status=data["status"],
            student=StudentDTO(
                id=UUID(student["id"]),
                user_id=UUID(student["user_id"]),
                education_level=student.get("education_level"),
                learning_goal=student.get("learning_goal"),
                timezone=student.get("timezone"),
                status=student["status"],
            )
            if student
            else None,
        )

    def _auth_response(self, data: dict) -> AuthResponse:
        return AuthResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            user=self._user(data["user"]),
        )
