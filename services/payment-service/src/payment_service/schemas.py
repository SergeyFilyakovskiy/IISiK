from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PaymentDTO:
    id: UUID
    booking_id: UUID
    student_id: UUID
    teacher_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    refunded_at: datetime | None
    failure_reason: str | None
    refund_reason: str | None
