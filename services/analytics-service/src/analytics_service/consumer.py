from decimal import Decimal
from uuid import UUID

from shared.errors import DomainError, ErrorCode
from shared.kafka import EventEnvelope

from .service import AnalyticsService


class AnalyticsEventHandler:
    def __init__(self, service: AnalyticsService) -> None:
        self.service = service

    async def __call__(self, event: EventEnvelope) -> None:
        payload = event.payload
        try:
            if event.event_type == "booking.created":
                await self.service.record_booking_created(event.event_id, event.occurred_at.date())
            elif event.event_type == "payment.completed":
                await self.service.record_payment(
                    event.event_id,
                    UUID(str(payload["teacher_id"])),
                    event.occurred_at.date(),
                    Decimal(str(payload["amount"])),
                )
            elif event.event_type == "scheduling.lesson.completed":
                await self.service.record_lesson_completed(
                    event.event_id,
                    UUID(str(payload["teacher_id"])),
                    event.occurred_at.date(),
                )
            elif event.event_type == "review.created":
                await self.service.record_review(
                    event.event_id,
                    UUID(str(payload["teacher_id"])),
                    event.occurred_at.date(),
                    int(payload["rating"]),
                )
        except (KeyError, TypeError, ValueError) as error:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Invalid analytics event payload"
            ) from error
