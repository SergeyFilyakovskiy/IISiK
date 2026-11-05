import asyncio
import os

from redis.asyncio import Redis

from shared.cache import RedisJsonCache
from shared.database import Database
from shared.kafka import KafkaEventConsumer
from shared.logging import configure_logging

from .cache import CatalogCache
from .consumer import CatalogEventHandler
from .grpc_server import create_grpc_server
from .service import CatalogService


async def serve() -> None:
    configure_logging(service="catalog-service", level=os.getenv("LOG_LEVEL", "INFO"))
    database = Database(os.environ["DATABASE_URL"])
    redis = Redis.from_url(os.getenv("CACHE_REDIS_URL", "redis://redis-cache:6379/0"))
    cache = CatalogCache(
        RedisJsonCache(redis, "catalog", int(os.getenv("CACHE_TTL_SECONDS", "60")))
    )
    service = CatalogService(database, cache)
    consumer = KafkaEventConsumer(
        os.getenv("KAFKA_BROKERS", "kafka:9092"),
        ["review.created"],
        "catalog-service",
        CatalogEventHandler(service),
        dlq_topic="catalog.dlq",
    )
    server = create_grpc_server(service, int(os.getenv("GRPC_PORT", "50052")))
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
        await redis.aclose()
        await database.close()


if __name__ == "__main__":
    asyncio.run(serve())
