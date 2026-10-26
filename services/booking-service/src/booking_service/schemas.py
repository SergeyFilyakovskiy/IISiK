from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BookingDTO:
    id: UUID
    lesson_id: UUID
    student_id: UUID
    teacher_id: UUID
    subject_id: UUID
    status: str
    price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
