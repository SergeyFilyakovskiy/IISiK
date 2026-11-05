import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventConsumer
from shared.logging import configure_logging

from .consumer import AnalyticsEventHandler
from .grpc_server import create_grpc_server
from .service import AnalyticsService


async def serve() -> None:
    configure_logging(service="analytics-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    service = AnalyticsService(database)
    consumer = KafkaEventConsumer(
        os.getenv("KAFKA_BROKERS", "kafka:9092"),
        ["booking.created", "payment.completed", "scheduling.lesson.completed", "review.created"],
        "analytics-service",
        AnalyticsEventHandler(service),
        dlq_topic="analytics.dlq",
    )
    server = create_grpc_server(service, int(os.getenv("GRPC_PORT", "50058")))
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
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
