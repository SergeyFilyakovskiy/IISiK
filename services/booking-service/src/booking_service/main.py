import asyncio
import os

from shared.database import Database
from shared.kafka import KafkaEventProducer
from shared.logging import configure_logging

from .clients import CatalogClient, PaymentClient, SchedulingClient
from .grpc_server import create_grpc_server
from .service import BookingService
from .workflows import BookingWorkflowService


async def serve() -> None:
    configure_logging(service="booking-service", level=os.getenv("LOG_LEVEL", "INFO"))
    timeout = float(os.getenv("GRPC_TIMEOUT_SECONDS", "5"))
    database = Database(os.environ["DATABASE_URL"])
    scheduling = SchedulingClient(
        os.getenv("SCHEDULING_GRPC_ADDRESS", "scheduling-service:50053"), timeout
    )
    payment = PaymentClient(os.getenv("PAYMENT_GRPC_ADDRESS", "payment-service:50055"), timeout)
    catalog = CatalogClient(os.getenv("CATALOG_GRPC_ADDRESS", "catalog-service:50052"), timeout)
    workflows = BookingWorkflowService(BookingService(database), scheduling, payment, catalog)
    events = KafkaEventProducer(os.getenv("KAFKA_BROKERS", "kafka:9092"), "booking-service")
    server = create_grpc_server(workflows, int(os.getenv("GRPC_PORT", "50054")), events)
    await events.start()
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await events.stop()
        await asyncio.gather(scheduling.close(), payment.close(), catalog.close())
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
