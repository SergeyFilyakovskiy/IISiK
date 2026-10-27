from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.database import Database

from .repositories import BookingRepository
from .schemas import BookingDTO


class BookingService:
    def __init__(self, database: Database) -> None:
        self.repository = BookingRepository(database)

    async def create_booking(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        subject_id: UUID,
        price: Decimal,
        currency: str,
    ) -> BookingDTO:
        return await self.repository.create_booking(
            lesson_id, student_id, teacher_id, subject_id, price, currency
        )

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        return await self.repository.get_booking(booking_id)

    async def confirm_booking(self, booking_id: UUID, paid_at: datetime) -> BookingDTO:
        return await self.repository.confirm_booking(booking_id, paid_at)

    async def cancel_booking(self, booking_id: UUID, reason: str | None) -> BookingDTO:
        return await self.repository.cancel_booking(booking_id, reason)

    async def complete_booking(self, booking_id: UUID, completed_at: datetime) -> BookingDTO:
        return await self.repository.complete_booking(booking_id, completed_at)

    async def list_bookings(
        self,
        student_id: UUID,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort_by: str = "CREATED_AT",
        sort_direction: str = "DESC",
    ) -> list[BookingDTO]:
        return await self.repository.list_bookings(
            student_id,
            status,
            created_from,
            created_to,
            min_price,
            max_price,
            sort_by,
            sort_direction,
        )
