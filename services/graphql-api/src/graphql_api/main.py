from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from shared.logging import configure_logging, correlation_id_var

from .auth_client import AuthClient
from .bff import BffService
from .config import get_settings
from .context import RequestAuth
from .gateways import (
    AnalyticsGateway,
    BookingGateway,
    CatalogGateway,
    IdentityGateway,
    NotificationGateway,
    PaymentGateway,
    ReviewGateway,
    SchedulingGateway,
)
from .schema import schema


def get_context(request: Request) -> dict:
    try:
        correlation_id = UUID(request.headers.get("x-correlation-id", str(uuid4())))
    except ValueError:
        correlation_id = uuid4()
    correlation_id_var.set(str(correlation_id))
    bff = request.app.state.bff
    return {
        "bff": bff,
        "auth": RequestAuth(request.headers.get("authorization"), bff.auth, bff.catalog),
        "correlation_id": correlation_id,
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(service="graphql-api")
    timeout = settings.grpc_timeout_seconds
    auth = AuthClient(settings.auth_service_url, timeout)
    catalog = CatalogGateway(settings.catalog_grpc_address, timeout)
    app.state.bff = BffService(
        auth=auth,
        identity=IdentityGateway(settings.identity_grpc_address, timeout),
        catalog=catalog,
        scheduling=SchedulingGateway(settings.scheduling_grpc_address, timeout),
        booking=BookingGateway(settings.booking_grpc_address, timeout),
        payment=PaymentGateway(settings.payment_grpc_address, timeout),
        review=ReviewGateway(settings.review_grpc_address, timeout),
        notification=NotificationGateway(settings.notification_grpc_address, timeout),
        analytics=AnalyticsGateway(settings.analytics_grpc_address, timeout),
    )
    try:
        yield
    finally:
        await app.state.bff.close()


app = FastAPI(title="Tutoring GraphQL API", version="1.0.0", lifespan=lifespan)
app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
