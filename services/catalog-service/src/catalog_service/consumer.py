from decimal import Decimal
from uuid import UUID

from shared.kafka import EventEnvelope

from .service import CatalogService


class CatalogEventHandler:
    def __init__(self, service: CatalogService) -> None:
        self.service = service

    async def __call__(self, event: EventEnvelope) -> None:
        if event.event_type != "review.created":
            return
        await self.service.recalculate_rating(
            UUID(str(event.payload["teacher_id"])),
            Decimal(str(event.payload["average_rating"])),
            int(event.payload["reviews_count"]),
        )
