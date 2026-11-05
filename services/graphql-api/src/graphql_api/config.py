from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_service_url: str = "http://identity-service:8001"
    identity_grpc_address: str = "identity-service:50051"
    catalog_grpc_address: str = "catalog-service:50052"
    scheduling_grpc_address: str = "scheduling-service:50053"
    booking_grpc_address: str = "booking-service:50054"
    payment_grpc_address: str = "payment-service:50055"
    review_grpc_address: str = "review-service:50056"
    notification_grpc_address: str = "notification-service:50057"
    analytics_grpc_address: str = "analytics-service:50058"
    grpc_timeout_seconds: float = Field(default=5, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
