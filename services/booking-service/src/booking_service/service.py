from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.database import Database
from shared.errors import DomainError, ErrorCode

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
        if not price.is_finite() or price < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Booking price must be finite and non-negative"
            )
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Currency must contain 3 characters")
        return await self.repository.create_booking(
            lesson_id, student_id, teacher_id, subject_id, price, normalized_currency
        )

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        return await self.repository.get_booking(booking_id)

    async def get_booking_by_lesson(self, lesson_id: UUID) -> BookingDTO | None:
        return await self.repository.get_booking_by_lesson(lesson_id)

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
        normalized_status = status.strip().upper() if status is not None else None
        if normalized_status is not None and normalized_status not in {
            "PENDING_PAYMENT",
            "CONFIRMED",
            "COMPLETED",
            "CANCELLED",
        }:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported booking status")
        if created_from is not None and created_to is not None and created_from > created_to:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "created_from must not be later than created_to"
            )
        if min_price is not None and (not min_price.is_finite() or min_price < 0):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "min_price must be finite and non-negative"
            )
        if max_price is not None and (not max_price.is_finite() or max_price < 0):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "max_price must be finite and non-negative"
            )
        if min_price is not None and max_price is not None and min_price > max_price:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "min_price must not be greater than max_price"
            )
        normalized_sort_by = sort_by.upper()
        if normalized_sort_by not in {"CREATED_AT", "PRICE", "UPDATED_AT"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported booking sort field")
        normalized_sort_direction = sort_direction.upper()
        if normalized_sort_direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported sort direction")

        return await self.repository.list_bookings(
            student_id,
            normalized_status,
            created_from,
            created_to,
            min_price,
            max_price,
            normalized_sort_by,
            normalized_sort_direction,
        )
