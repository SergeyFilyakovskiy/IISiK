from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .models import Payment
from .schemas import PaymentDTO


class PaymentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_payment(
        self,
        booking_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        amount: Decimal,
        currency: str,
        payment_method: str,
    ) -> PaymentDTO:
        async with self.database.session() as session:
            try:
                async with session.begin():
                    payment = await session.scalar(
                        select(Payment).where(Payment.booking_id == booking_id)
                    )
                    if payment is None:
                        payment = Payment(
                            booking_id=booking_id,
                            student_id=student_id,
                            teacher_id=teacher_id,
                            amount=amount,
                            currency=currency,
                            payment_method=payment_method,
                            status="CREATED",
                        )
                        session.add(payment)
                        await session.flush()
            except IntegrityError as error:
                payment = await session.scalar(
                    select(Payment).where(Payment.booking_id == booking_id)
                )
                if payment is None:
                    raise DomainError(ErrorCode.CONFLICT, "Payment could not be created") from error
            return self._to_dto(payment)

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        async with self.database.session() as session:
            payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
            if payment is None:
                return None
            return self._to_dto(payment)

    async def mark_payment_succeeded(self, payment_id: UUID, paid_at: datetime) -> PaymentDTO:
        return await self._transition_payment(
            payment_id,
            ("CREATED", "PROCESSING"),
            {"status": "SUCCEEDED", "paid_at": paid_at},
        )

    async def fail_payment(self, payment_id: UUID, reason: str) -> PaymentDTO:
        return await self._transition_payment(
            payment_id,
            ("CREATED", "PROCESSING"),
            {"status": "FAILED", "failure_reason": reason},
        )

    async def refund_payment(
        self,
        payment_id: UUID,
        reason: str | None = None,
        refunded_at: datetime | None = None,
    ) -> PaymentDTO:
        return await self._transition_payment(
            payment_id,
            ("SUCCEEDED",),
            {
                "status": "REFUNDED",
                "refund_reason": reason,
                "refunded_at": refunded_at if refunded_at is not None else func.now(),
            },
        )

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
        statement = select(Payment).where(Payment.student_id == student_id)
        if status is not None:
            statement = statement.where(Payment.status == status)
        if created_from is not None:
            statement = statement.where(Payment.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(Payment.created_at <= created_to)
        if min_amount is not None:
            statement = statement.where(Payment.amount >= min_amount)
        if max_amount is not None:
            statement = statement.where(Payment.amount <= max_amount)

        sort_columns = {
            "CREATED_AT": Payment.created_at,
            "AMOUNT": Payment.amount,
            "UPDATED_AT": Payment.updated_at,
        }
        sort_column = sort_columns.get(sort_by.upper())
        if sort_column is None:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported payment sort field")
        direction = sort_direction.upper()
        if direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported sort direction")
        order_by = sort_column.asc() if direction == "ASC" else sort_column.desc()
        statement = statement.order_by(order_by)

        async with self.database.session() as session:
            payments = await session.scalars(statement)
            return [self._to_dto(payment) for payment in payments]

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        async with self.database.session() as session:
            payment = await session.scalar(select(Payment).where(Payment.booking_id == booking_id))
            if payment is None:
                return None
            return self._to_dto(payment)

    async def _transition_payment(
        self,
        payment_id: UUID,
        expected_statuses: tuple[str, ...],
        values: dict[str, object],
    ) -> PaymentDTO:
        async with self.database.session() as session:
            async with session.begin():
                payment = await session.scalar(
                    update(Payment)
                    .where(
                        Payment.id == payment_id,
                        Payment.status.in_(expected_statuses),
                    )
                    .values(**values, updated_at=func.now())
                    .returning(Payment)
                )
                if payment is None:
                    current_status = await session.scalar(
                        select(Payment.status).where(Payment.id == payment_id)
                    )
                    if current_status is None:
                        raise DomainError(ErrorCode.NOT_FOUND, "Payment not found")
                    raise DomainError(
                        ErrorCode.CONFLICT,
                        f"Payment cannot be changed from status {current_status}",
                    )
            return self._to_dto(payment)

    @staticmethod
    def _to_dto(payment: Payment) -> PaymentDTO:
        return PaymentDTO(
            id=payment.id,
            booking_id=payment.booking_id,
            student_id=payment.student_id,
            teacher_id=payment.teacher_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            status=payment.status,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            paid_at=payment.paid_at,
            refunded_at=payment.refunded_at,
            failure_reason=payment.failure_reason,
            refund_reason=payment.refund_reason,
        )
