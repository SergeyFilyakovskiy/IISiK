from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .repositories import PaymentRepository
from .schemas import PaymentDTO


class PaymentService:
    def __init__(self, database: Database) -> None:
        self.repository = PaymentRepository(database)

    async def create_payment(
        self,
        booking_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        amount: Decimal,
        currency: str,
        payment_method: str,
    ) -> PaymentDTO:
        if amount < 0:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Payment amount must be non-negative")
        return await self.repository.create_payment(
            booking_id, student_id, teacher_id, amount, currency, payment_method
        )

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        return await self.repository.get_payment(payment_id)

    async def mark_payment_succeeded(self, payment_id: UUID, paid_at: datetime) -> PaymentDTO:
        return await self.repository.mark_payment_succeeded(payment_id, paid_at)

    async def fail_payment(self, payment_id: UUID, reason: str) -> PaymentDTO:
        return await self.repository.fail_payment(payment_id, reason)

    async def refund_payment(
        self,
        payment_id: UUID,
        reason: str | None = None,
        refunded_at: datetime | None = None,
    ) -> PaymentDTO:
        return await self.repository.refund_payment(payment_id, reason, refunded_at)

    async def list_payments(
        self,
        student_id: UUID,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        sort_by: str = "CREATED_AT",
        sort_direction: str = "DESC",
    ) -> list[PaymentDTO]:
        return await self.repository.list_payments(
            student_id,
            status,
            created_from,
            created_to,
            min_amount,
            max_amount,
            sort_by,
            sort_direction,
        )

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        return await self.repository.get_payment_by_booking(booking_id)
