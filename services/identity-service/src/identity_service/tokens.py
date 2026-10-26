from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from redis.asyncio import Redis

from .config import Settings
from .errors import ErrorCode, IdentityError

ROTATE_REFRESH_SCRIPT = """
if redis.call("GET", KEYS[1]) ~= ARGV[1] then
    return 0
end
if redis.call("DEL", KEYS[1]) ~= 1 then
    return 0
end
redis.call("SET", KEYS[2], ARGV[2], "EX", tonumber(ARGV[3]))
return 1
"""


@dataclass(frozen=True)
class TokenPayload:
    subject: UUID
    jti: UUID
    token_type: str
    expires_at: datetime


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
    def refresh_key(jti: UUID) -> str:
        return f"identity:refresh:{jti}"

    @staticmethod
    def blacklist_key(jti: UUID) -> str:
        return f"identity:access_blacklist:{jti}"

    def encode(self, user_id: UUID, token_type: str, ttl_seconds: int) -> tuple[str, TokenPayload]:
        now = datetime.now(UTC)
        payload = TokenPayload(user_id, uuid4(), token_type, now + timedelta(seconds=ttl_seconds))
        token = jwt.encode(
            {
                "sub": str(payload.subject),
                "jti": str(payload.jti),
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
                required=["sub", "jti", "type", "iat", "exp"],
            )
            if claims["type"] != expected_type:
                raise ValueError("Unexpected token type")
            return TokenPayload(
                subject=UUID(claims["sub"]),
                jti=UUID(claims["jti"]),
                token_type=claims["type"],
                expires_at=datetime.fromtimestamp(claims["exp"], UTC),
            )
        except (JWTError, KeyError, TypeError, ValueError) as error:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Invalid or expired token") from error

    async def issue_pair(self, user_id: UUID) -> AuthTokens:
        access_token, _ = self.encode(user_id, "access", self.settings.access_ttl_seconds)
        refresh_token, refresh = self.encode(user_id, "refresh", self.settings.refresh_ttl_seconds)
        await self.redis.set(
            self.refresh_key(refresh.jti),
            str(user_id),
            ex=self.settings.refresh_ttl_seconds,
        )
        return AuthTokens(access_token, refresh_token, self.settings.access_ttl_seconds)

    async def rotate_refresh(self, token: str) -> AuthTokens:
        refresh = self.decode(token, "refresh")
        access_token, _ = self.encode(refresh.subject, "access", self.settings.access_ttl_seconds)
        new_token, new_refresh = self.encode(
            refresh.subject, "refresh", self.settings.refresh_ttl_seconds
        )
        rotated = await self.redis.eval(
            ROTATE_REFRESH_SCRIPT,
            2,
            self.refresh_key(refresh.jti),
            self.refresh_key(new_refresh.jti),
            str(refresh.subject),
            str(refresh.subject),
            self.settings.refresh_ttl_seconds,
        )
        if rotated != 1:
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Refresh token is no longer valid")
        return AuthTokens(access_token, new_token, self.settings.access_ttl_seconds)

    async def validate_access(self, token: str) -> TokenPayload:
        payload = self.decode(token, "access")
        if await self.redis.exists(self.blacklist_key(payload.jti)):
            raise IdentityError(ErrorCode.INVALID_TOKEN, "Access token has been revoked")
        return payload

    async def blacklist_access(self, payload: TokenPayload) -> None:
        ttl = max(int((payload.expires_at - datetime.now(UTC)).total_seconds()), 1)
        await self.redis.set(self.blacklist_key(payload.jti), "1", ex=ttl)

    async def revoke_refresh(self, token: str) -> TokenPayload:
        payload = self.decode(token, "refresh")
        await self.redis.delete(self.refresh_key(payload.jti))
        return payload
