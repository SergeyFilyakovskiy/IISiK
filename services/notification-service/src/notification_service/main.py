import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventConsumer
from shared.logging import configure_logging

from .consumer import NotificationEventHandler
from .grpc_server import create_grpc_server
from .identity_client import IdentityClient
from .service import NotificationService


async def serve() -> None:
    configure_logging(service="notification-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    service = NotificationService(database)
    identity = IdentityClient(
        os.getenv("IDENTITY_GRPC_ADDRESS", "identity-service:50051"),
        float(os.getenv("GRPC_TIMEOUT_SECONDS", "5")),
    )
    consumer = KafkaEventConsumer(
        os.getenv("KAFKA_BROKERS", "kafka:9092"),
        [
            "booking.created",
            "booking.cancelled",
            "payment.completed",
            "booking.completed",
        ],
        "notification-service",
        NotificationEventHandler(service, identity),
        dlq_topic="notification.dlq",
    )
    server = create_grpc_server(service, int(os.getenv("GRPC_PORT", "50057")))
    await consumer.start()
    await server.start()
    task = asyncio.create_task(consumer.run())
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await consumer.stop()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await identity.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
