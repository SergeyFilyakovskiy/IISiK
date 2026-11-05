from uuid import UUID

from shared.kafka import EventEnvelope, KafkaEventProducer
from shared.logging import get_log_context


async def publish_event(
    producer: KafkaEventProducer,
    topic: str,
    event_type: str,
    aggregate_id: UUID,
    payload: dict,
) -> EventEnvelope:
    correlation = get_log_context().get("correlation_id")
    event = EventEnvelope.create(
        event_type,
        aggregate_id,
        payload,
        UUID(correlation) if correlation else None,
    )
    await producer.publish(topic, event)
    return event
