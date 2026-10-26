from functools import wraps

import grpc
from identity.v1 import identity_pb2, identity_pb2_grpc
from pydantic import ValidationError

from .auth_service import AuthService
from .errors import ErrorCode, IdentityError
from .models import User
from .schemas import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RoleCode,
    StudentProfileInput,
)

error_statuses = {
    ErrorCode.EMAIL_EXISTS: grpc.StatusCode.ALREADY_EXISTS,
    ErrorCode.INVALID_CREDENTIALS: grpc.StatusCode.UNAUTHENTICATED,
    ErrorCode.INVALID_TOKEN: grpc.StatusCode.UNAUTHENTICATED,
    ErrorCode.INVALID_REGISTRATION: grpc.StatusCode.INVALID_ARGUMENT,
    ErrorCode.USER_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
    ErrorCode.USER_INACTIVE: grpc.StatusCode.PERMISSION_DENIED,
}


def grpc_errors(func):
    @wraps(func)
    async def wrapper(self, request, context):
        try:
            return await func(self, request, context)
        except ValidationError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid request")
        except IdentityError as error:
            await context.abort(error_statuses[error.code], error.message)

    return wrapper


def user_to_proto(user: User):
    message = identity_pb2.User(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=identity_pb2.Role.Value(user.role if isinstance(user.role, str) else user.role.code),
        status=user.status,
    )
    if user.student is not None:
        student = identity_pb2.StudentProfile(id=str(user.student.id), status=user.student.status)
        for field in ("education_level", "learning_goal", "timezone"):
            value = getattr(user.student, field)
            if value is not None:
                setattr(student, field, value)
        message.student.CopyFrom(student)
    return message


def auth_to_proto(response: AuthResponse):
    return identity_pb2.AuthResponse(
        access_token=response.access_token,
        refresh_token=response.refresh_token,
        token_type=response.token_type,
        expires_in=response.expires_in,
        user=user_to_proto(response.user),
    )


def student_profile_to_schema(request) -> StudentProfileInput | None:
    if not request.HasField("student_profile"):
        return None
    values = {}
    for field in ("education_level", "learning_goal", "timezone"):
        if request.student_profile.HasField(field):
            values[field] = getattr(request.student_profile, field)
    return StudentProfileInput(**values)


async def get_access_token(context) -> str:
    metadata = {key.lower(): value for key, value in context.invocation_metadata()}
    authorization = metadata.get("authorization", "")
    if not authorization.startswith("Bearer "):
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Bearer token is required")
    return authorization.removeprefix("Bearer ")


class IdentityServicer(identity_pb2_grpc.IdentityServiceServicer):
    def __init__(self, service: AuthService) -> None:
        self.service = service

    @grpc_errors
    async def Register(self, request, context):
        try:
            role = RoleCode(identity_pb2.Role.Name(request.role))
        except ValueError as error:
            raise IdentityError(
                ErrorCode.INVALID_REGISTRATION, "Public registration requires STUDENT or TEACHER"
            ) from error
        response = await self.service.register(
            RegisterRequest(
                email=request.email,
                password=request.password,
                full_name=request.full_name,
                role=role,
                student_profile=student_profile_to_schema(request),
            )
        )
        return auth_to_proto(response)

    @grpc_errors
    async def Login(self, request, context):
        response = await self.service.login(
            LoginRequest(email=request.email, password=request.password)
        )
        return auth_to_proto(response)

    @grpc_errors
    async def Refresh(self, request, context):
        response = await self.service.refresh(RefreshRequest(refresh_token=request.refresh_token))
        return auth_to_proto(response)

    @grpc_errors
    async def Logout(self, request, context):
        access_token = await get_access_token(context)
        await self.service.logout(access_token, request.refresh_token)
        return identity_pb2.LogoutResponse(success=True)

    @grpc_errors
    async def GetUser(self, request, context):
        access_token = await get_access_token(context)
        return user_to_proto(await self.service.get_user(access_token))

    @grpc_errors
    async def ValidateToken(self, request, context):
        access_token = await get_access_token(context)
        return user_to_proto(await self.service.get_user(access_token))


def create_grpc_server(service: AuthService, port: int):
    server = grpc.aio.server()
    identity_pb2_grpc.add_IdentityServiceServicer_to_server(IdentityServicer(service), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
