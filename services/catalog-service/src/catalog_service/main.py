import asyncio
import os

from shared.database import Database
from shared.logging import configure_logging

from .grpc_server import create_grpc_server
from .service import CatalogService


async def serve() -> None:
    configure_logging(service="catalog-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    server = create_grpc_server(CatalogService(database), int(os.getenv("GRPC_PORT", "50052")))
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
