import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from strawberry.fastapi import GraphQLRouter

from shared.database import Database

from .bff import BffService
from .config import get_settings
from .gateways import (
    MockAnalyticsGateway,
    MockBookingGateway,
    MockCatalogGateway,
    MockIdentityGateway,
    MockNotificationGateway,
    MockPaymentGateway,
    MockReviewGateway,
    MockSchedulingGateway,
)
from .schema import schema


async def get_context(request: Request) -> dict[str, BffService]:
    return {"bff": request.app.state.bff}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    databases = {
        name: Database(url)
        for name, url in (
            ("identity", settings.identity_database_url),
            ("catalog", settings.catalog_database_url),
            ("scheduling", settings.scheduling_database_url),
            ("booking", settings.booking_database_url),
            ("payment", settings.payment_database_url),
            ("review", settings.review_database_url),
            ("notification", settings.notification_database_url),
            ("analytics", settings.analytics_database_url),
        )
    }
    app.state.databases = databases
    app.state.bff = BffService(
        identity=MockIdentityGateway(databases["identity"]),
        catalog=MockCatalogGateway(databases["catalog"]),
        scheduling=MockSchedulingGateway(databases["scheduling"]),
        booking=MockBookingGateway(databases["booking"]),
        payment=MockPaymentGateway(databases["payment"]),
        review=MockReviewGateway(databases["review"]),
        notification=MockNotificationGateway(databases["notification"]),
        analytics=MockAnalyticsGateway(databases["analytics"]),
    )
    try:
        yield
    finally:
        await asyncio.gather(*(database.close() for database in databases.values()))


app = FastAPI(title="Tutoring GraphQL API", version="0.1.0", lifespan=lifespan)
app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    async def check(database: Database) -> None:
        async with database.session() as session:
            await session.execute(text("SELECT 1"))

    try:
        await asyncio.gather(
            *(check(database) for database in request.app.state.databases.values())
        )
    except SQLAlchemyError as error:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Databases are unavailable") from error
    return {"status": "ok"}
