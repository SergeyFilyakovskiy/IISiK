import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .config import Settings
from .errors import ErrorCode, IdentityError

logger = logging.getLogger(__name__)

ISSUE_SESSION_SCRIPT = """
redis.call("HSET", KEYS[1], "sub", ARGV[1], "access_jti", ARGV[2])
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[3]))
redis.call("SET", KEYS[2], ARGV[4], "EX", tonumber(ARGV[3]))
return 1
"""

ROTATE_REFRESH_SCRIPT = """
if redis.call("GET", KEYS[1]) ~= ARGV[1] then
    return 0
end
if redis.call("HGET", KEYS[2], "sub") ~= ARGV[2] then
    return 0
end
local old_access_jti = redis.call("HGET", KEYS[2], "access_jti")
if not old_access_jti then
    return 0
end
redis.call("DEL", KEYS[1], KEYS[2])
redis.call(
    "SET",
    "identity:access_blacklist:" .. old_access_jti,
    "1",
    "EX",
    tonumber(ARGV[3])
)
redis.call("HSET", KEYS[2], "sub", ARGV[2], "access_jti", ARGV[4])
redis.call("EXPIRE", KEYS[2], tonumber(ARGV[5]))
redis.call("SET", KEYS[3], ARGV[1], "EX", tonumber(ARGV[5]))
return 1
"""

VALIDATE_ACCESS_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) == 1 then
    return 0
end
if redis.call("HGET", KEYS[2], "sub") ~= ARGV[1] then
    return 0
end
if redis.call("HGET", KEYS[2], "access_jti") ~= ARGV[2] then
    return 0
end
return 1
"""

REVOKE_SESSION_SCRIPT = """
if redis.call("GET", KEYS[1]) ~= ARGV[1] then
    return 0
end
if redis.call("HGET", KEYS[2], "sub") ~= ARGV[2] then
    return 0
end
if redis.call("HGET", KEYS[2], "access_jti") ~= ARGV[3] then
    return 0
end
redis.call("DEL", KEYS[1], KEYS[2])
redis.call("SET", KEYS[3], "1", "EX", tonumber(ARGV[4]))
return 1
"""


@dataclass(frozen=True)
class TokenPayload:
    subject: UUID
    jti: UUID
    token_type: str
    expires_at: datetime
    session_id: UUID


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    expires_in: int


class TokenManager:
    def __init__(self, settings: Settings, redis: Redis) -> None:
        self.settings = settings
        self.redis = redis
        self.secret = settings.jwt_secret.get_secret_value()

    @staticmethod
    def session_key(sid: UUID) -> str:
        return f"identity:session:{sid}"

    @staticmethod
    def refresh_key(jti: UUID) -> str:
        return f"identity:refresh:{jti}"

    @staticmethod
    def blacklist_key(jti: UUID) -> str:
        return f"identity:access_blacklist:{jti}"

    @staticmethod
    def _session_store_error(operation: str, sid: UUID, error: RedisError) -> IdentityError:
        logger.error(
            "identity_session_store_unavailable",
            extra={
                "operation": operation,
                "session_id": str(sid),
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return IdentityError(
            ErrorCode.SESSION_STORE_UNAVAILABLE,
            "Authentication session store is unavailable",
        )

    def encode(
        self,
        user_id: UUID,
        token_type: str,
        ttl_seconds: int,
        session_id: UUID | None = None,
    ) -> tuple[str, TokenPayload]:
        now = datetime.now(UTC)
        payload = TokenPayload(
            subject=user_id,
            jti=uuid4(),
            token_type=token_type,
            expires_at=now + timedelta(seconds=ttl_seconds),
            session_id=session_id or uuid4(),
        )
        token = jwt.encode(
            {
                "sub": str(payload.subject),
                "jti": str(payload.jti),
                "sid": str(payload.session_id),
                "type": payload.token_type,
                "iat": now,
                "exp": payload.expires_at,
            },
            self.secret,
            algorithm=self.settings.jwt_algorithm,
        )
        return token, payload

    def decode(self, token: str, expected_type: str) -> TokenPayload:
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=[self.settings.jwt_algorithm],
                required=["sub", "jti", "sid", "type", "iat", "exp"],
            )
            if claims["type"] != expected_type:
                raise ValueError("Unexpected token type")
            return TokenPayload(
                subject=UUID(claims["sub"]),
                jti=UUID(claims["jti"]),
                token_type=claims["type"],
                expires_at=datetime.fromtimestamp(claims["exp"], UTC),
                session_id=UUID(claims["sid"]),
            )
        except (JWTError, KeyError, TypeError, ValueError) as error:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Invalid or expired token") from error

    async def issue_pair(self, user_id: UUID) -> AuthTokens:
        sid = uuid4()
        access_token, access = self.encode(user_id, "access", self.settings.access_ttl_seconds, sid)
        refresh_token, refresh = self.encode(
            user_id, "refresh", self.settings.refresh_ttl_seconds, sid
        )
        try:
            await self.redis.eval(
                ISSUE_SESSION_SCRIPT,
                2,
                self.session_key(sid),
                self.refresh_key(refresh.jti),
                str(user_id),
                str(access.jti),
                self.settings.refresh_ttl_seconds,
                str(sid),
            )
        except RedisError as error:
            raise self._session_store_error("issue_session", sid, error) from error
        logger.info(
            "identity_session_issued",
            extra={"user_id": str(user_id), "session_id": str(sid)},
        )
        return AuthTokens(access_token, refresh_token, self.settings.access_ttl_seconds)

    async def rotate_refresh(self, token: str) -> AuthTokens:
        refresh = self.decode(token, "refresh")
        sid = refresh.session_id
        access_token, access = self.encode(
            refresh.subject, "access", self.settings.access_ttl_seconds, sid
        )
        new_token, new_refresh = self.encode(
            refresh.subject, "refresh", self.settings.refresh_ttl_seconds, sid
        )
        try:
            rotated = await self.redis.eval(
                ROTATE_REFRESH_SCRIPT,
                3,
                self.refresh_key(refresh.jti),
                self.session_key(sid),
                self.refresh_key(new_refresh.jti),
                str(sid),
                str(refresh.subject),
                self.settings.access_ttl_seconds,
                str(access.jti),
                self.settings.refresh_ttl_seconds,
            )
        except RedisError as error:
            raise self._session_store_error("rotate_session", sid, error) from error
        if rotated != 1:
            logger.warning(
                "identity_session_rotation_rejected",
                extra={"user_id": str(refresh.subject), "session_id": str(sid)},
            )
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Refresh token is no longer valid")
        logger.info(
            "identity_session_rotated",
            extra={"user_id": str(refresh.subject), "session_id": str(sid)},
        )
        return AuthTokens(access_token, new_token, self.settings.access_ttl_seconds)

    async def validate_access(self, token: str) -> TokenPayload:
        payload = self.decode(token, "access")
        try:
            valid = await self.redis.eval(
                VALIDATE_ACCESS_SCRIPT,
                2,
                self.blacklist_key(payload.jti),
                self.session_key(payload.session_id),
                str(payload.subject),
                str(payload.jti),
            )
        except RedisError as error:
            raise self._session_store_error("validate_access", payload.session_id, error) from error
        if valid != 1:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Access token session is no longer active")
        return payload

    async def revoke_session(self, access: TokenPayload, refresh: TokenPayload) -> None:
        ttl = max(int((access.expires_at - datetime.now(UTC)).total_seconds()), 1)
        try:
            revoked = await self.redis.eval(
                REVOKE_SESSION_SCRIPT,
                3,
                self.refresh_key(refresh.jti),
                self.session_key(access.session_id),
                self.blacklist_key(access.jti),
                str(access.session_id),
                str(access.subject),
                str(access.jti),
                ttl,
            )
        except RedisError as error:
            raise self._session_store_error("revoke_session", access.session_id, error) from error
        if revoked != 1:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Session is no longer active")
        logger.info(
            "identity_session_revoked",
            extra={"user_id": str(access.subject), "session_id": str(access.session_id)},
        )
