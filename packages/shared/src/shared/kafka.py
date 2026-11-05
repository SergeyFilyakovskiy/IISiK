import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition

from shared.logging import log_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    event_id: UUID
    occurred_at: datetime
    correlation_id: UUID
    schema_version: int = 1

    @classmethod
    def create(
        cls,
        event_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
    ) -> "EventEnvelope":
        return cls(
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload,
            event_id=uuid4(),
            occurred_at=datetime.now(UTC),
            correlation_id=correlation_id or uuid4(),
        )

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "event_id": str(self.event_id),
                "event_type": self.event_type,
                "schema_version": self.schema_version,
                "occurred_at": self.occurred_at.isoformat(),
                "aggregate_id": str(self.aggregate_id),
                "correlation_id": str(self.correlation_id),
                "payload": self.payload,
            },
            default=str,
            separators=(",", ":"),
        ).encode()

    @classmethod
    def from_bytes(cls, value: bytes) -> "EventEnvelope":
        try:
            data = json.loads(value)
            event = cls(
                event_id=UUID(data["event_id"]),
                event_type=str(data["event_type"]),
                schema_version=int(data["schema_version"]),
                occurred_at=datetime.fromisoformat(data["occurred_at"]),
                aggregate_id=UUID(data["aggregate_id"]),
                correlation_id=UUID(data["correlation_id"]),
                payload=dict(data["payload"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("Invalid event envelope") from error
        if event.schema_version != 1 or not event.event_type.strip():
            raise ValueError("Unsupported event envelope")
        return event


class KafkaEventProducer:
    def __init__(self, brokers: str, client_id: str) -> None:
        self.producer = AIOKafkaProducer(
            bootstrap_servers=brokers,
            client_id=client_id,
            enable_idempotence=True,
        )

    async def start(self) -> None:
        await self.producer.start()

    async def stop(self) -> None:
        await self.producer.stop()

    async def publish(self, topic: str, event: EventEnvelope) -> None:
        headers = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "correlation_id": str(event.correlation_id),
            "schema_version": str(event.schema_version),
        }
        with log_context(
            operation="kafka.publish",
            correlation_id=str(event.correlation_id),
            event_id=str(event.event_id),
        ):
            await self.producer.send_and_wait(
                topic,
                event.to_bytes(),
                key=str(event.aggregate_id).encode(),
                headers=[(key, value.encode()) for key, value in headers.items()],
            )
            logger.info("event_published", extra={"topic": topic, "event_type": event.event_type})


class KafkaEventConsumer:
    def __init__(
        self,
        brokers: str,
        topics: Iterable[str],
        group_id: str,
        handler: Callable[[EventEnvelope], Awaitable[None]],
        *,
        dlq_topic: str,
        max_attempts: int = 3,
        retry_delay: float = 0.2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=brokers,
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        self.handler = handler
        self.dlq = KafkaEventProducer(brokers, f"{group_id}-dlq")
        self.dlq_topic = dlq_topic
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        await self.dlq.start()
        await self.consumer.start()

    async def stop(self) -> None:
        self._stopped.set()
        await self.consumer.stop()
        await self.dlq.stop()

    async def run(self) -> None:
        async for message in self.consumer:
            if self._stopped.is_set():
                break
            try:
                event = EventEnvelope.from_bytes(message.value)
            except ValueError as error:
                await self._send_to_dlq(message, None, error)
                await self._commit(message)
                continue

            with log_context(
                operation="kafka.consume",
                correlation_id=str(event.correlation_id),
                event_id=str(event.event_id),
            ):
                for attempt in range(1, self.max_attempts + 1):
                    try:
                        await self.handler(event)
                        await self._commit(message)
                        logger.info(
                            "event_processed",
                            extra={"topic": message.topic, "event_type": event.event_type},
                        )
                        break
                    except Exception as error:
                        logger.exception(
                            "event_processing_failed",
                            extra={"topic": message.topic, "attempt": attempt},
                        )
                        if attempt == self.max_attempts:
                            await self._send_to_dlq(message, event, error)
                            await self._commit(message)
                        else:
                            await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))

    async def _commit(self, message) -> None:
        await self.consumer.commit(
            {TopicPartition(message.topic, message.partition): message.offset + 1}
        )

    async def _send_to_dlq(self, message, event: EventEnvelope | None, error: Exception) -> None:
        dlq_event = EventEnvelope.create(
            "system.dead_letter",
            event.aggregate_id if event else uuid4(),
            {
                "source_topic": message.topic,
                "source_partition": message.partition,
                "source_offset": message.offset,
                "error_type": type(error).__name__,
                "raw_value": message.value.decode(errors="replace"),
            },
            event.correlation_id if event else None,
        )
        await self.dlq.publish(self.dlq_topic, dlq_event)
