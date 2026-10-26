from uuid import UUID

from shared.database import Database

from .repositories import BookingRepository
from .schemas import BookingDTO


class BookingService:
    def __init__(self, database: Database) -> None:
        self.repository = BookingRepository(database)

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        return await self.repository.get_booking(booking_id)

    async def list_bookings(self, student_id: UUID, status: str | None = None) -> list[BookingDTO]:
        return await self.repository.list_bookings(student_id, status)
