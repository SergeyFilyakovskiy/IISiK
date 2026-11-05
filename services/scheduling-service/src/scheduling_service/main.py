import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventProducer
from shared.logging import configure_logging

from .clients import CatalogClient
from .grpc_server import create_grpc_server
from .service import SchedulingService
from .workflows import SchedulingWorkflowService


async def serve() -> None:
    configure_logging(service="scheduling-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    catalog = CatalogClient(
        os.getenv("CATALOG_GRPC_ADDRESS", "catalog-service:50052"),
        float(os.getenv("GRPC_TIMEOUT_SECONDS", "5")),
    )
    workflows = SchedulingWorkflowService(SchedulingService(database), catalog)
    events = KafkaEventProducer(os.getenv("KAFKA_BROKERS", "kafka:9092"), "scheduling-service")
    server = create_grpc_server(workflows, int(os.getenv("GRPC_PORT", "50053")), events)
    await events.start()
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await events.stop()
        await catalog.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
