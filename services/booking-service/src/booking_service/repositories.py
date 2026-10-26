from uuid import UUID

from sqlalchemy import select

from shared.database import Database

from .models import Booking
from .schemas import BookingDTO


class BookingRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        async with self.database.session() as session:
            booking = await session.scalar(select(Booking).where(Booking.id == booking_id))
            if booking is None:
                return None
            return self._to_dto(booking)

    async def list_bookings(self, student_id: UUID, status: str | None = None) -> list[BookingDTO]:
        statement = select(Booking).where(Booking.student_id == student_id)
        if status is not None:
            statement = statement.where(Booking.status == status)
        statement = statement.order_by(Booking.created_at.desc())

        async with self.database.session() as session:
            bookings = await session.scalars(statement)
            return [self._to_dto(booking) for booking in bookings]

    @staticmethod
    def _to_dto(booking: Booking) -> BookingDTO:
        return BookingDTO(
            id=booking.id,
            lesson_id=booking.lesson_id,
            student_id=booking.student_id,
            teacher_id=booking.teacher_id,
            subject_id=booking.subject_id,
            status=booking.status,
            price=booking.price,
            currency=booking.currency,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            paid_at=booking.paid_at,
            completed_at=booking.completed_at,
            cancelled_at=booking.cancelled_at,
            cancel_reason=booking.cancel_reason,
        )
