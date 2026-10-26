from uuid import UUID

from shared.database import Database

from .repositories import PaymentRepository
from .schemas import PaymentDTO


class PaymentService:
    def __init__(self, database: Database) -> None:
        self.repository = PaymentRepository(database)

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        return await self.repository.get_payment(payment_id)

    async def list_payments(self, student_id: UUID) -> list[PaymentDTO]:
        return await self.repository.list_payments(student_id)

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        return await self.repository.get_payment_by_booking(booking_id)
