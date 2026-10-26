from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .auth_service import AuthService
from .errors import ErrorCode, IdentityError
from .mappers import to_user_response
from .models import User
from .schemas import (
    AuthResponse,
    HealthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
error_statuses = {
    ErrorCode.EMAIL_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_REGISTRATION: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.USER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.USER_INACTIVE: status.HTTP_403_FORBIDDEN,
}


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def identity_error_handler(_: Request, error: IdentityError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if error.code == ErrorCode.INVALID_TOKEN else None
    return JSONResponse(
        status_code=error_statuses[error.code],
        content={"detail": error.message, "code": error.code},
        headers=headers,
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    try:
        async with request.app.state.database.session() as session:
            await session.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except (SQLAlchemyError, RedisError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity dependencies are unavailable",
        ) from error
    return HealthResponse(status="ok")


@router.post("/api/v1/auth/register", response_model=AuthResponse, status_code=201, tags=["auth"])
async def register(
    data: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return await service.register(data)


@router.post("/api/v1/auth/login", response_model=AuthResponse, tags=["auth"])
async def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return await service.login(data)


@router.post("/api/v1/auth/refresh", response_model=AuthResponse, tags=["auth"])
async def refresh(
    data: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return await service.refresh(data)


@router.post("/api/v1/auth/logout", status_code=204, tags=["auth"])
async def logout(
    data: LogoutRequest,
    access_token: Annotated[str, Depends(get_access_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.logout(access_token, data.refresh_token)
    return Response(status_code=204)


@router.get("/api/v1/users/me", response_model=UserResponse, tags=["users"])
async def me(
    access_token: Annotated[str, Depends(get_access_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user: User = await service.get_user(access_token)
    return to_user_response(user)
