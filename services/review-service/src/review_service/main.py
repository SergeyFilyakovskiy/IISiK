import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventProducer
from shared.logging import configure_logging

from .clients import BookingClient
from .grpc_server import create_grpc_server
from .service import ReviewService
from .workflows import ReviewWorkflowService


async def serve() -> None:
    configure_logging(service="review-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    booking = BookingClient(
        os.getenv("BOOKING_GRPC_ADDRESS", "booking-service:50054"),
        float(os.getenv("GRPC_TIMEOUT_SECONDS", "5")),
    )
    workflows = ReviewWorkflowService(ReviewService(database), booking)
    events = KafkaEventProducer(os.getenv("KAFKA_BROKERS", "kafka:9092"), "review-service")
    server = create_grpc_server(workflows, int(os.getenv("GRPC_PORT", "50056")), events)
    await events.start()
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await events.stop()
        await booking.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
