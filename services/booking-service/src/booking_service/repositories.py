from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .models import Booking
from .schemas import BookingDTO


class BookingRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_booking(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        subject_id: UUID,
        price: Decimal,
        currency: str,
    ) -> BookingDTO:
        async with self.database.session() as session:
            try:
                async with session.begin():
                    booking = Booking(
                        lesson_id=lesson_id,
                        student_id=student_id,
                        teacher_id=teacher_id,
                        subject_id=subject_id,
                        price=price,
                        currency=currency,
                        status="PENDING_PAYMENT",
                    )
                    session.add(booking)
                    await session.flush()
            except IntegrityError as error:
                raise DomainError(
                    ErrorCode.CONFLICT, "Booking for this lesson already exists"
                ) from error
            return self._to_dto(booking)

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        async with self.database.session() as session:
            booking = await session.scalar(select(Booking).where(Booking.id == booking_id))
            if booking is None:
                return None
            return self._to_dto(booking)

    async def confirm_booking(self, booking_id: UUID, paid_at: datetime) -> BookingDTO:
        return await self._transition_booking(
            booking_id,
            ("PENDING_PAYMENT",),
            {"status": "CONFIRMED", "paid_at": paid_at},
        )

    async def cancel_booking(self, booking_id: UUID, reason: str | None) -> BookingDTO:
        return await self._transition_booking(
            booking_id,
            ("PENDING_PAYMENT", "CONFIRMED"),
            {
                "status": "CANCELLED",
                "cancelled_at": func.now(),
                "cancel_reason": reason,
            },
        )

    async def complete_booking(self, booking_id: UUID, completed_at: datetime) -> BookingDTO:
        return await self._transition_booking(
            booking_id,
            ("CONFIRMED",),
            {"status": "COMPLETED", "completed_at": completed_at},
        )

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
        statement = select(Booking).where(Booking.student_id == student_id)
        if status is not None:
            statement = statement.where(Booking.status == status)
        if created_from is not None:
            statement = statement.where(Booking.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(Booking.created_at <= created_to)
        if min_price is not None:
            statement = statement.where(Booking.price >= min_price)
        if max_price is not None:
            statement = statement.where(Booking.price <= max_price)

        sort_columns = {
            "CREATED_AT": Booking.created_at,
            "PRICE": Booking.price,
            "UPDATED_AT": Booking.updated_at,
        }
        sort_column = sort_columns.get(sort_by.upper())
        if sort_column is None:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported booking sort field")
        direction = sort_direction.upper()
        if direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported sort direction")
        order_by = sort_column.asc() if direction == "ASC" else sort_column.desc()
        statement = statement.order_by(order_by)

        async with self.database.session() as session:
            bookings = await session.scalars(statement)
            return [self._to_dto(booking) for booking in bookings]

    async def _transition_booking(
        self,
        booking_id: UUID,
        expected_statuses: tuple[str, ...],
        values: dict[str, object],
    ) -> BookingDTO:
        async with self.database.session() as session:
            async with session.begin():
                booking = await session.scalar(
                    update(Booking)
                    .where(
                        Booking.id == booking_id,
                        Booking.status.in_(expected_statuses),
                    )
                    .values(**values, updated_at=func.now())
                    .returning(Booking)
                )
                if booking is None:
                    current_status = await session.scalar(
                        select(Booking.status).where(Booking.id == booking_id)
                    )
                    if current_status is None:
                        raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
                    raise DomainError(
                        ErrorCode.CONFLICT,
                        f"Booking cannot be changed from status {current_status}",
                    )
            return self._to_dto(booking)

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
