import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventProducer
from shared.logging import configure_logging

from .grpc_server import create_grpc_server
from .service import PaymentService


async def serve() -> None:
    configure_logging(service="payment-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    events = KafkaEventProducer(os.getenv("KAFKA_BROKERS", "kafka:9092"), "payment-service")
    server = create_grpc_server(
        PaymentService(database), int(os.getenv("GRPC_PORT", "50055")), events
    )
    await events.start()
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await events.stop()
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
