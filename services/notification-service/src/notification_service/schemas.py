from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NotificationDTO:
    id: UUID
    user_id: UUID
    event_type: str
    title: str
    body: str
    status: str
    source_event_id: UUID | None
    created_at: datetime
    sent_at: datetime | None
