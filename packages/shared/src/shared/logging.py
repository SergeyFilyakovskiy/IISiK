import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

service_var: ContextVar[str | None] = ContextVar("service", default=None)
operation_var: ContextVar[str | None] = ContextVar("operation", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
event_id_var: ContextVar[str | None] = ContextVar("event_id", default=None)

_STANDARD_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__)
_CONTEXT_ATTRIBUTES = frozenset({"service", "operation", "correlation_id", "event_id"})
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "payload",
    "private_key",
    "secret",
    "token",
)


def get_log_context() -> dict[str, str]:
    values = {
        "service": service_var.get(),
        "operation": operation_var.get(),
        "correlation_id": correlation_id_var.get(),
        "event_id": event_id_var.get(),
    }
    return {key: value for key, value in values.items() if value is not None}


@contextmanager
def log_context(
    *,
    service: str | None = None,
    operation: str | None = None,
    correlation_id: str | None = None,
    event_id: str | None = None,
) -> Iterator[None]:
    values = {
        "service": service,
        "operation": operation,
        "correlation_id": correlation_id,
        "event_id": event_id,
    }
    variables = {
        "service": service_var,
        "operation": operation_var,
        "correlation_id": correlation_id_var,
        "event_id": event_id_var,
    }
    tokens = [
        (variables[key], variables[key].set(value))
        for key, value in values.items()
        if value is not None
    ]
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


class JsonFormatter(logging.Formatter):
    def __init__(self, *, max_value_length: int = 512) -> None:
        super().__init__()
        self.max_value_length = max_value_length

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._shorten(message),
            **get_log_context(),
        }
        for key in _CONTEXT_ATTRIBUTES:
            value = getattr(record, key, None)
            if value is not None:
                data[key] = self._shorten(str(value))
        for key, value in record.__dict__.items():
            if (
                key not in _STANDARD_RECORD_ATTRIBUTES
                and key not in _CONTEXT_ATTRIBUTES
                and not key.startswith("_")
                and not _is_sensitive_key(key)
            ):
                data[key] = self._safe_value(value)
        if record.exc_info:
            data["exception"] = self._shorten(self.formatException(record.exc_info), 4_000)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)

    def _safe_value(self, value: Any) -> Any:
        if value is None or isinstance(value, bool | int | float):
            return value
        if isinstance(value, str | UUID | datetime | Enum):
            return self._shorten(str(value))
        return self._shorten(str(value))

    def _shorten(self, value: str, limit: int | None = None) -> str:
        max_length = limit or self.max_value_length
        if len(value) <= max_length:
            return value
        return f"{value[: max_length - 1]}…"


def configure_logging(
    *,
    service: str | None = None,
    level: int | str = logging.INFO,
) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    if service is not None:
        service_var.set(service)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)
