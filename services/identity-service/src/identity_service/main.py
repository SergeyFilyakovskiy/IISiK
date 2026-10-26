from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from shared.database import Database

from .api import identity_error_handler, router
from .auth_service import AuthService
from .config import get_settings
from .errors import IdentityError
from .grpc_server import create_grpc_server
from .tokens import TokenManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    tokens = TokenManager(settings, redis)
    auth_service = AuthService(database, tokens)
    grpc_server = create_grpc_server(auth_service, settings.grpc_port)

    app.state.database = database
    app.state.redis = redis
    app.state.auth_service = auth_service

    await grpc_server.start()
    try:
        yield
    finally:
        await grpc_server.stop(grace=5)
        await redis.aclose()
        await database.close()


app = FastAPI(
    title="Identity Service",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.add_exception_handler(IdentityError, identity_error_handler)
