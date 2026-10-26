from uuid import UUID

from sqlalchemy import select

from shared.database import Database

from .models import Payment
from .schemas import PaymentDTO


class PaymentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        async with self.database.session() as session:
            payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
            if payment is None:
                return None
            return self._to_dto(payment)

    async def list_payments(self, student_id: UUID) -> list[PaymentDTO]:
        statement = (
            select(Payment)
            .where(Payment.student_id == student_id)
            .order_by(Payment.created_at.desc())
        )
        async with self.database.session() as session:
            payments = await session.scalars(statement)
            return [self._to_dto(payment) for payment in payments]

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        async with self.database.session() as session:
            payment = await session.scalar(select(Payment).where(Payment.booking_id == booking_id))
            if payment is None:
                return None
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
