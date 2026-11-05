import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.auth import (
    CurrentUser,
    Role,
    require_role,
    require_student_owner,
    require_teacher_owner,
)
from shared.errors import DomainError, ErrorCode

from .clients import CatalogClient, PaymentClient, SchedulingClient
from .schemas import BookingDTO
from .service import BookingService

logger = logging.getLogger(__name__)


class BookingWorkflowService:
    def __init__(
        self,
        service: BookingService,
        scheduling: SchedulingClient,
        payment: PaymentClient,
        catalog: CatalogClient,
    ) -> None:
        self.service = service
        self.scheduling = scheduling
        self.payment = payment
        self.catalog = catalog

    @staticmethod
    def _authorize_read(actor: CurrentUser, booking: BookingDTO) -> None:
        if actor.role is Role.ADMIN:
            return
        if actor.role is Role.STUDENT:
            require_student_owner(actor, booking.student_id)
            return
        if actor.role is Role.TEACHER:
            require_teacher_owner(actor, booking.teacher_id)
            return
        raise DomainError(ErrorCode.FORBIDDEN, "Booking access is forbidden")

    async def get_booking(self, actor: CurrentUser, booking_id: UUID) -> BookingDTO | None:
        booking = await self.service.get_booking(booking_id)
        if booking is not None:
            self._authorize_read(actor, booking)
        return booking

    async def get_booking_by_lesson(self, actor: CurrentUser, lesson_id: UUID) -> BookingDTO | None:
        booking = await self.service.get_booking_by_lesson(lesson_id)
        if booking is not None:
            self._authorize_read(actor, booking)
        return booking

    async def list_bookings(self, actor: CurrentUser, student_id: UUID | None, **filters):
        if actor.role is Role.ADMIN and student_id is not None:
            selected_student = student_id
        else:
            if actor.student_id is None:
                raise DomainError(ErrorCode.FORBIDDEN, "Student profile is required")
            selected_student = actor.student_id
        return await self.service.list_bookings(selected_student, **filters)

    async def book_lesson(self, actor: CurrentUser, lesson_id: UUID) -> BookingDTO:
        require_role(actor, Role.STUDENT)
        if actor.student_id is None:
            raise DomainError(ErrorCode.FORBIDDEN, "Student profile is required")
        lesson = await self.scheduling.get_lesson(str(lesson_id), actor)
        if lesson is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
        teacher, subject = await asyncio.gather(
            self.catalog.get_teacher(lesson.teacher_id, actor),
            self.catalog.get_subject(lesson.subject_id, actor),
        )
        if teacher is None or subject is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Catalog data not found")
        if teacher.profile_status != "ACTIVE" or not subject.is_active:
            raise DomainError(ErrorCode.CONFLICT, "Lesson is not available for booking")
        reserved = await self.scheduling.reserve(str(lesson_id), actor)
        try:
            return await self.service.create_booking(
                lesson_id,
                actor.student_id,
                UUID(teacher.id),
                UUID(subject.id),
                Decimal(reserved.price),
                reserved.currency,
            )
        except Exception:
            await self._compensate(self.scheduling.release(str(lesson_id), actor))
            raise

    async def pay_booking(
        self, actor: CurrentUser, booking_id: UUID, payment_method: str, idempotency_key: UUID
    ) -> BookingDTO:
        booking = await self.get_booking(actor, booking_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        require_role(actor, Role.STUDENT)
        require_student_owner(actor, booking.student_id)
        if booking.status == "CONFIRMED":
            await self.scheduling.mark_booked(str(booking.lesson_id), actor)
            return booking
        if booking.status != "PENDING_PAYMENT":
            raise DomainError(ErrorCode.CONFLICT, "Booking cannot be paid in its current status")
        payment = await self.payment.process(booking, payment_method, str(idempotency_key), actor)
        if payment.status != "SUCCEEDED":
            raise DomainError(ErrorCode.CONFLICT, "Payment failed")
        try:
            confirmed = await self.service.confirm_booking(
                booking_id, datetime.fromisoformat(payment.paid_at)
            )
            await self.scheduling.mark_booked(str(booking.lesson_id), actor)
            return confirmed
        except Exception:
            await self._compensate(
                self.service.cancel_booking(booking_id, "Payment compensation"),
                self.payment.refund(payment.id, "Payment compensation", actor),
                self.scheduling.release(str(booking.lesson_id), actor),
            )
            raise

    async def cancel_booking(
        self, actor: CurrentUser, booking_id: UUID, reason: str | None
    ) -> BookingDTO:
        booking = await self.get_booking(actor, booking_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        if booking.status not in {"PENDING_PAYMENT", "CONFIRMED", "CANCELLED"}:
            raise DomainError(ErrorCode.CONFLICT, "Booking cannot be cancelled in its status")
        if booking.status != "CANCELLED":
            booking = await self.service.cancel_booking(booking_id, reason)
        payment = await self.payment.get_by_booking(str(booking_id), actor)
        if payment is not None and payment.status == "SUCCEEDED":
            await self.payment.refund(payment.id, reason, actor)
        await self.scheduling.release(str(booking.lesson_id), actor)
        return booking

    async def cancel_lesson(
        self, actor: CurrentUser, lesson_id: UUID, reason: str | None
    ) -> tuple[BookingDTO | None, object]:
        require_role(actor, Role.TEACHER, admin_override=True)
        booking = await self.service.get_booking_by_lesson(lesson_id)
        if booking is not None:
            require_teacher_owner(actor, booking.teacher_id)
            if booking.status != "CANCELLED":
                await self.cancel_booking(actor, booking.id, reason)
        lesson = await self.scheduling.cancel(str(lesson_id), reason, actor)
        return booking, lesson

    async def complete_lesson(self, actor: CurrentUser, lesson_id: UUID) -> BookingDTO:
        require_role(actor, Role.TEACHER, admin_override=True)
        booking = await self.service.get_booking_by_lesson(lesson_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        require_teacher_owner(actor, booking.teacher_id)
        if booking.status == "COMPLETED":
            return booking
        if booking.status != "CONFIRMED":
            raise DomainError(ErrorCode.CONFLICT, "Only a confirmed booking can be completed")
        await self.scheduling.complete(str(lesson_id), actor)
        return await self.service.complete_booking(booking.id, datetime.now().astimezone())

    @staticmethod
    async def _compensate(*operations) -> None:
        results = await asyncio.gather(*operations, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error("booking_compensation_failed", exc_info=result)
