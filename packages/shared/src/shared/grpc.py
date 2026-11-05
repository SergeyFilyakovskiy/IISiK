import asyncio
import math
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from functools import wraps
from typing import Never, TypeVar

import grpc
import grpc.aio

from shared.auth import CurrentUser, principal_from_metadata, principal_to_metadata
from shared.errors import DomainError, ErrorCode
from shared.logging import get_log_context, log_context

CORRELATION_ID_METADATA_KEY = "correlation-id"
DOMAIN_ERROR_CODE_METADATA_KEY = "domain-error-code"


def observe_rpc(func):
    @wraps(func)
    async def wrapper(self, request, context):
        correlation_id = extract_correlation_id(context.invocation_metadata())
        with log_context(operation=func.__name__, correlation_id=correlation_id):
            return await func(self, request, context)

    return wrapper


Metadata = Mapping[str, str | bytes] | Iterable[tuple[str, str | bytes]]
RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

_ERROR_STATUS = {
    ErrorCode.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
    ErrorCode.VALIDATION_ERROR: grpc.StatusCode.INVALID_ARGUMENT,
    ErrorCode.CONFLICT: grpc.StatusCode.FAILED_PRECONDITION,
    ErrorCode.UNAUTHENTICATED: grpc.StatusCode.UNAUTHENTICATED,
    ErrorCode.FORBIDDEN: grpc.StatusCode.PERMISSION_DENIED,
    ErrorCode.TIMEOUT: grpc.StatusCode.DEADLINE_EXCEEDED,
    ErrorCode.UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
}
_STATUS_ERROR = {
    grpc.StatusCode.INVALID_ARGUMENT: ErrorCode.VALIDATION_ERROR,
    grpc.StatusCode.OUT_OF_RANGE: ErrorCode.VALIDATION_ERROR,
    grpc.StatusCode.NOT_FOUND: ErrorCode.NOT_FOUND,
    grpc.StatusCode.ALREADY_EXISTS: ErrorCode.CONFLICT,
    grpc.StatusCode.FAILED_PRECONDITION: ErrorCode.CONFLICT,
    grpc.StatusCode.ABORTED: ErrorCode.CONFLICT,
    grpc.StatusCode.UNAUTHENTICATED: ErrorCode.UNAUTHENTICATED,
    grpc.StatusCode.PERMISSION_DENIED: ErrorCode.FORBIDDEN,
    grpc.StatusCode.DEADLINE_EXCEEDED: ErrorCode.TIMEOUT,
}
_RETRYABLE_STATUSES = frozenset({grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED})


def domain_error_to_status(error: DomainError) -> grpc.StatusCode:
    return _ERROR_STATUS[error.code]


async def abort_with_domain_error(
    context: grpc.aio.ServicerContext,
    error: DomainError,
) -> Never:
    await context.abort(
        domain_error_to_status(error),
        error.message,
        trailing_metadata=((DOMAIN_ERROR_CODE_METADATA_KEY, error.code.value),),
    )


def metadata_dict(metadata: Metadata | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in _metadata_items(metadata):
        if isinstance(value, bytes):
            result[key.lower()] = value.decode("ascii", errors="replace")
        else:
            result[key.lower()] = value
    return result


def extract_correlation_id(metadata: Metadata | None) -> str | None:
    return metadata_dict(metadata).get(CORRELATION_ID_METADATA_KEY) or None


def extract_principal(metadata: Metadata | None) -> CurrentUser:
    return principal_from_metadata(metadata_dict(metadata))


def build_client_metadata(
    metadata: Metadata | None = None,
    *,
    principal: CurrentUser | None = None,
    correlation_id: str | None = None,
) -> tuple[tuple[str, str | bytes], ...]:
    propagated_keys = {CORRELATION_ID_METADATA_KEY}
    if principal is not None:
        propagated_keys.update(principal_to_metadata(principal))
    items = [
        (key.lower(), value)
        for key, value in _metadata_items(metadata)
        if key.lower() not in propagated_keys
    ]
    resolved_correlation_id = correlation_id or get_log_context().get("correlation_id")
    if resolved_correlation_id:
        items.append((CORRELATION_ID_METADATA_KEY, resolved_correlation_id))
    if principal is not None:
        items.extend(principal_to_metadata(principal).items())
    return tuple(items)


def domain_error_from_rpc_error(error: grpc.aio.AioRpcError) -> DomainError:
    metadata = metadata_dict(error.trailing_metadata())
    metadata.update(metadata_dict(error.initial_metadata()))
    code_value = metadata.get(DOMAIN_ERROR_CODE_METADATA_KEY)
    try:
        code = ErrorCode(code_value) if code_value else _status_to_error_code(error.code())
    except ValueError:
        code = _status_to_error_code(error.code())
    message = error.details() or f"gRPC call failed with {error.code().name}"
    return DomainError(code, message)


def raise_domain_error(error: grpc.aio.AioRpcError) -> Never:
    raise domain_error_from_rpc_error(error) from error


async def call_with_policy(
    call: Callable[..., Awaitable[ResponseT]],
    request: RequestT,
    *,
    timeout: float = 5.0,
    retry: bool = False,
    max_attempts: int = 3,
    initial_backoff: float = 0.1,
    max_backoff: float = 2.0,
    metadata: Metadata | None = None,
    principal: CurrentUser | None = None,
    correlation_id: str | None = None,
) -> ResponseT:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    if initial_backoff < 0 or max_backoff < 0:
        raise ValueError("backoff values must not be negative")
    attempts = max_attempts if retry else 1
    call_metadata = build_client_metadata(
        metadata,
        principal=principal,
        correlation_id=correlation_id,
    )
    for attempt in range(attempts):
        try:
            return await call(request, timeout=timeout, metadata=call_metadata)
        except grpc.aio.AioRpcError as error:
            can_retry = attempt + 1 < attempts and error.code() in _RETRYABLE_STATUSES
            if not can_retry:
                raise_domain_error(error)
            backoff = min(max_backoff, initial_backoff * (2**attempt))
            if backoff:
                await asyncio.sleep(backoff)
    raise AssertionError("unreachable")


def create_channel(
    target: str,
    *,
    secure: bool = False,
    credentials: grpc.ChannelCredentials | None = None,
    options: Sequence[tuple[str, object]] | None = None,
) -> grpc.aio.Channel:
    channel_options = tuple(options) if options is not None else None
    if credentials is not None:
        return grpc.aio.secure_channel(target, credentials, options=channel_options)
    if secure:
        return grpc.aio.secure_channel(
            target,
            grpc.ssl_channel_credentials(),
            options=channel_options,
        )
    return grpc.aio.insecure_channel(target, options=channel_options)


def _metadata_items(metadata: Metadata | None) -> Iterable[tuple[str, str | bytes]]:
    if metadata is None:
        return ()
    if isinstance(metadata, Mapping):
        return metadata.items()
    return metadata


def _status_to_error_code(status: grpc.StatusCode) -> ErrorCode:
    return _STATUS_ERROR.get(status, ErrorCode.UNAVAILABLE)
