from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    identity_database_url: str
    catalog_database_url: str
    scheduling_database_url: str
    booking_database_url: str
    payment_database_url: str
    review_database_url: str
    notification_database_url: str
    analytics_database_url: str
    identity_redis_url: str
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = Field(default=5, gt=0)
    jwt_refresh_ttl_days: int = Field(default=30, gt=0)

    @property
    def access_ttl_seconds(self) -> int:
        return self.jwt_access_ttl_minutes * 60

    @property
    def refresh_ttl_seconds(self) -> int:
        return self.jwt_refresh_ttl_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
