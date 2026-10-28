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
        if not amount.is_finite() or amount < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Payment amount must be finite and non-negative"
            )
        normalized_payment_method = payment_method.strip()
        if not normalized_payment_method:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Payment method must not be blank")
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Currency must contain 3 characters")
        return await self.repository.create_payment(
            booking_id,
            student_id,
            teacher_id,
            amount,
            normalized_currency,
            normalized_payment_method,
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
        normalized_status = status.strip().upper() if status is not None else None
        if normalized_status is not None and normalized_status not in {
            "CREATED",
            "PROCESSING",
            "SUCCEEDED",
            "FAILED",
            "REFUNDED",
        }:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported payment status")
        if created_from is not None and created_to is not None and created_from > created_to:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "created_from must not be later than created_to"
            )
        if min_amount is not None and (not min_amount.is_finite() or min_amount < 0):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "min_amount must be finite and non-negative"
            )
        if max_amount is not None and (not max_amount.is_finite() or max_amount < 0):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "max_amount must be finite and non-negative"
            )
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "min_amount must not be greater than max_amount"
            )
        normalized_sort_by = sort_by.upper()
        if normalized_sort_by not in {"CREATED_AT", "AMOUNT", "UPDATED_AT"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported payment sort field")
        normalized_sort_direction = sort_direction.upper()
        if normalized_sort_direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported sort direction")

        return await self.repository.list_payments(
            student_id,
            normalized_status,
            created_from,
            created_to,
            min_amount,
            max_amount,
            normalized_sort_by,
            normalized_sort_direction,
        )

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        return await self.repository.get_payment_by_booking(booking_id)
