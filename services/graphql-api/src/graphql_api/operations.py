import asyncio
import logging
from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from shared.errors import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class BusinessOperations:
    async def create_teacher_profile(
        self,
        user_id: UUID,
        about: str | None,
        experience_years: int,
        price_per_lesson: Decimal,
        currency: str,
        subject_ids: list[UUID],
    ):
        user = await self.identity.get_user(user_id)
        if user is None:
            raise DomainError(ErrorCode.NOT_FOUND, "User not found")
        if user.role != "TEACHER":
            raise DomainError(ErrorCode.FORBIDDEN, "Teacher profile requires a teacher user")
        teacher = await self.catalog.create_teacher_profile(
            user_id, about, experience_years, price_per_lesson, currency, subject_ids
        )
        return await self.get_teacher(teacher.id)

    async def update_teacher_profile(self, teacher_id: UUID, **changes):
        teacher = await self.catalog.update_teacher_profile(teacher_id, **changes)
        return await self.get_teacher(teacher.id)

    async def add_teacher_subject(
        self, teacher_id: UUID, subject_id: UUID, proficiency_level: str | None
    ):
        teacher = await self.catalog.add_teacher_subject(teacher_id, subject_id, proficiency_level)
        return await self.get_teacher(teacher.id)

    async def remove_teacher_subject(self, teacher_id: UUID, subject_id: UUID):
        teacher = await self.catalog.remove_teacher_subject(teacher_id, subject_id)
        return await self.get_teacher(teacher.id)

    async def create_subject(self, name: str, description: str | None, is_active: bool):
        return await self.catalog.create_subject(name, description, is_active)

    async def update_subject(self, subject_id: UUID, **changes):
        return await self.catalog.update_subject(subject_id, **changes)

    async def create_schedule_slot(
        self, teacher_id: UUID, weekday: int, start_time: time, end_time: time
    ):
        if await self.catalog.get_teacher(teacher_id) is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Teacher not found")
        return await self.scheduling.create_schedule_slot(teacher_id, weekday, start_time, end_time)

    async def update_schedule_slot(self, slot_id: UUID, **changes):
        return await self.scheduling.update_schedule_slot(slot_id, **changes)

    async def delete_schedule_slot(self, slot_id: UUID) -> bool:
        return await self.scheduling.delete_schedule_slot(slot_id)

    async def create_lesson(
        self,
        teacher_id: UUID,
        subject_id: UUID,
        schedule_slot_id: UUID | None,
        start_at: datetime,
        duration_minutes: int,
    ):
        teacher = await self.catalog.get_teacher(teacher_id)
        if teacher is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Teacher not found")
        if teacher.profile_status != "ACTIVE":
            raise DomainError(ErrorCode.CONFLICT, "Teacher profile is inactive")
        subject = await self.catalog.get_subject(subject_id)
        if subject is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Subject not found")
        if not subject.is_active:
            raise DomainError(ErrorCode.CONFLICT, "Subject is inactive")
        lesson = await self.scheduling.create_lesson(
            teacher_id,
            subject_id,
            schedule_slot_id,
            start_at,
            duration_minutes,
            teacher.price_per_lesson,
            teacher.currency,
        )
        return await self.get_lesson(lesson.id)

    async def cancel_lesson(self, lesson_id: UUID, reason: str | None):
        lesson = await self.scheduling.cancel_lesson(lesson_id, reason)
        return await self.get_lesson(lesson.id)

    async def reschedule_lesson(self, lesson_id: UUID, new_start_at: datetime):
        lesson = await self.scheduling.reschedule_lesson(lesson_id, new_start_at)
        return await self.get_lesson(lesson.id)

    async def book_lesson(self, lesson_id: UUID, user_id: UUID):
        student = await self.identity.get_student_by_user_id(user_id)
        if student is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Student profile not found")
        lesson = await self.scheduling.get_lesson(lesson_id)
        if lesson is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
        teacher = await self.catalog.get_teacher(lesson.teacher_id)
        subject = await self.catalog.get_subject(lesson.subject_id)
        if teacher is None or subject is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson references missing catalog data")
        if teacher.profile_status != "ACTIVE" or not subject.is_active:
            raise DomainError(ErrorCode.CONFLICT, "Lesson is not available for booking")

        reserved = await self.scheduling.reserve_lesson(lesson_id)
        try:
            booking = await self.booking.create_booking(
                reserved.id,
                student.id,
                teacher.id,
                subject.id,
                reserved.price,
                reserved.currency,
            )
        except Exception:
            await self.scheduling.release_lesson(reserved.id)
            raise

        await self._side_effects(
            self.analytics.record_booking_created(booking.id, booking.created_at.date()),
            self.notification.create_notification(
                user_id,
                "BookingCreated",
                "Booking created",
                "Your lesson booking is pending payment",
                booking.id,
            ),
        )
        return await self.get_booking(booking.id)

    async def pay_booking(self, booking_id: UUID, payment_method: str):
        booking = await self.booking.get_booking(booking_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        existing = await self.payment.get_payment_by_booking(booking_id)
        if booking.status == "CONFIRMED" and existing is not None:
            return await self.get_booking(booking_id)
        if booking.status != "PENDING_PAYMENT":
            raise DomainError(ErrorCode.CONFLICT, "Booking cannot be paid in its current status")

        payment = existing or await self.payment.create_payment(
            booking.id,
            booking.student_id,
            booking.teacher_id,
            booking.price,
            booking.currency,
            payment_method,
        )
        if payment_method.upper() == "FAIL":
            await self.payment.fail_payment(payment.id, "Mock payment failure")
            raise DomainError(ErrorCode.CONFLICT, "Payment failed")
        if payment.status != "SUCCEEDED":
            payment = await self.payment.mark_payment_succeeded(
                payment.id, datetime.now().astimezone()
            )
        await self.booking.confirm_booking(booking_id, payment.paid_at)
        try:
            await self.scheduling.mark_lesson_booked(booking.lesson_id)
        except Exception:
            await self.booking.cancel_booking(booking_id, "Payment compensation")
            await self.payment.refund_payment(payment.id, "Payment compensation")
            await self.scheduling.release_lesson(booking.lesson_id)
            raise

        await self._side_effects(
            self.analytics.record_payment(
                payment.id, booking.teacher_id, payment.paid_at.date(), payment.amount
            ),
            self.notification.create_notification(
                booking.student_id,
                "PaymentCompleted",
                "Payment completed",
                "Your lesson payment has succeeded",
                payment.id,
            ),
        )
        return await self.get_booking(booking_id)

    async def cancel_booking(self, booking_id: UUID, reason: str | None):
        booking = await self.booking.get_booking(booking_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        if booking.status == "CANCELLED":
            return await self.get_booking(booking_id)
        booking = await self.booking.cancel_booking(booking_id, reason)
        payment = await self.payment.get_payment_by_booking(booking_id)
        if payment is not None and payment.status == "SUCCEEDED":
            await self.payment.refund_payment(payment.id, reason)
        await self.scheduling.release_lesson(booking.lesson_id)
        await self._side_effects(
            self.notification.create_notification(
                booking.student_id,
                "BookingCancelled",
                "Booking cancelled",
                reason or "Your booking has been cancelled",
                booking.id,
            )
        )
        return await self.get_booking(booking_id)

    async def mark_lesson_completed(self, lesson_id: UUID):
        booking = await self.booking.get_booking_by_lesson(lesson_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Booking not found")
        if booking.status != "CONFIRMED":
            raise DomainError(ErrorCode.CONFLICT, "Only a confirmed booking can be completed")
        lesson = await self.scheduling.complete_lesson(lesson_id)
        await self.booking.complete_booking(booking.id, datetime.now().astimezone())
        await self._side_effects(
            self.analytics.record_lesson_completed(
                booking.id, booking.teacher_id, booking.completed_at.date()
            ),
            self.notification.create_notification(
                booking.student_id,
                "LessonCompleted",
                "Lesson completed",
                "Your lesson has been completed",
                booking.id,
            ),
        )
        return await self.get_lesson(lesson.id)

    async def add_review(
        self,
        lesson_id: UUID,
        student_id: UUID,
        rating: int,
        comment: str | None,
    ):
        booking = await self.booking.get_booking_by_lesson(lesson_id)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Completed booking not found")
        if booking.status != "COMPLETED" or booking.student_id != student_id:
            raise DomainError(ErrorCode.FORBIDDEN, "Review requires a completed student booking")
        review = await self.review.create_review(
            lesson_id, student_id, booking.teacher_id, rating, comment
        )
        average, count = await self.review.get_rating_stats(booking.teacher_id)
        await self._side_effects(
            self.catalog.recalculate_rating(booking.teacher_id, average, count),
            self.analytics.record_review(
                review.id, booking.teacher_id, review.created_at.date(), rating
            ),
        )
        return review

    async def _side_effects(self, *operations) -> None:
        results = await asyncio.gather(*operations, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error("Post-operation side effect failed: %s", result)
