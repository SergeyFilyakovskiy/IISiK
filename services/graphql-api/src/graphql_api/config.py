from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
