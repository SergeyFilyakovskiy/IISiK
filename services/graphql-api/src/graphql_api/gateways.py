from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from analytics_service.schemas import AnalyticsReportDTO
from analytics_service.service import AnalyticsService
from booking_service.schemas import BookingDTO
from booking_service.service import BookingService
from catalog_service.schemas import (
    PageDTO,
    RatingDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
)
from catalog_service.service import CatalogService
from identity_service.auth_service import AuthService
from identity_service.read_schemas import StudentDTO, UserDTO
from identity_service.read_service import IdentityReadService
from identity_service.schemas import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from identity_service.write_service import IdentityWriteService
from notification_service.schemas import NotificationDTO
from notification_service.service import NotificationService
from payment_service.schemas import PaymentDTO
from payment_service.service import PaymentService
from review_service.schemas import PageDTO as ReviewPageDTO
from review_service.schemas import ReviewDTO
from review_service.service import ReviewService
from scheduling_service.schemas import LessonDTO, ScheduleSlotDTO
from scheduling_service.service import SchedulingService
from shared.database import Database


class IdentityGateway(Protocol):
    async def get_user(self, user_id: UUID) -> UserDTO | None: ...
    async def get_student(self, student_id: UUID) -> StudentDTO | None: ...
    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None: ...
    async def register(self, data: RegisterRequest) -> AuthResponse: ...
    async def login(self, data: LoginRequest) -> AuthResponse: ...
    async def refresh(self, data: RefreshRequest) -> AuthResponse: ...
    async def logout(self, access_token: str, refresh_token: str) -> None: ...
    async def update_student_profile(
        self,
        user_id: UUID,
        education_level: str | None,
        learning_goal: str | None,
        timezone: str | None,
    ) -> StudentDTO: ...


class CatalogGateway(Protocol):
    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None: ...
    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None: ...
    async def list_subjects(
        self, search: str | None, is_active: bool | None, sort_direction: str
    ) -> list[SubjectDTO]: ...
    async def list_teachers(
        self, filters: TeacherFilterDTO, page: int, page_size: int
    ) -> PageDTO[TeacherDTO]: ...
    async def create_teacher_profile(
        self,
        user_id: UUID,
        about: str | None,
        experience_years: int,
        price_per_lesson: Decimal,
        currency: str,
        subject_ids: list[UUID],
    ) -> TeacherDTO: ...
    async def update_teacher_profile(self, teacher_id: UUID, **changes) -> TeacherDTO: ...
    async def add_teacher_subject(
        self, teacher_id: UUID, subject_id: UUID, proficiency_level: str | None
    ) -> TeacherDTO: ...
    async def remove_teacher_subject(self, teacher_id: UUID, subject_id: UUID) -> TeacherDTO: ...
    async def create_subject(
        self, name: str, description: str | None, is_active: bool
    ) -> SubjectDTO: ...
    async def update_subject(self, subject_id: UUID, **changes) -> SubjectDTO: ...
    async def recalculate_rating(
        self, teacher_id: UUID, avg_rating: Decimal, reviews_count: int
    ) -> RatingDTO: ...


class SchedulingGateway(Protocol):
    async def get_lesson(self, lesson_id: UUID) -> LessonDTO | None: ...
    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlotDTO]: ...
    async def list_available_lessons(
        self,
        teacher_id: UUID | None,
        subject_id: UUID | None,
        start_from: datetime | None,
        end_to: datetime | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[LessonDTO]: ...
    async def create_schedule_slot(
        self, teacher_id: UUID, weekday: int, start_time: time, end_time: time
    ) -> ScheduleSlotDTO: ...
    async def update_schedule_slot(self, slot_id: UUID, **changes) -> ScheduleSlotDTO: ...
    async def delete_schedule_slot(self, slot_id: UUID) -> bool: ...
    async def create_lesson(
        self,
        teacher_id: UUID,
        subject_id: UUID,
        schedule_slot_id: UUID | None,
        start_at: datetime,
        duration_minutes: int,
        price: Decimal,
        currency: str,
    ) -> LessonDTO: ...
    async def cancel_lesson(self, lesson_id: UUID, reason: str | None) -> LessonDTO: ...
    async def reschedule_lesson(self, lesson_id: UUID, new_start_at: datetime) -> LessonDTO: ...
    async def reserve_lesson(self, lesson_id: UUID) -> LessonDTO: ...
    async def release_lesson(self, lesson_id: UUID) -> LessonDTO: ...
    async def mark_lesson_booked(self, lesson_id: UUID) -> LessonDTO: ...
    async def complete_lesson(self, lesson_id: UUID) -> LessonDTO: ...


class BookingGateway(Protocol):
    async def get_booking(self, booking_id: UUID) -> BookingDTO | None: ...
    async def get_booking_by_lesson(self, lesson_id: UUID) -> BookingDTO | None: ...
    async def list_bookings(
        self,
        student_id: UUID,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[BookingDTO]: ...
    async def create_booking(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        subject_id: UUID,
        price: Decimal,
        currency: str,
    ) -> BookingDTO: ...
    async def confirm_booking(self, booking_id: UUID, paid_at: datetime) -> BookingDTO: ...
    async def cancel_booking(self, booking_id: UUID, reason: str | None) -> BookingDTO: ...
    async def complete_booking(self, booking_id: UUID, completed_at: datetime) -> BookingDTO: ...


class PaymentGateway(Protocol):
    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None: ...
    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None: ...
    async def list_payments(
        self,
        student_id: UUID,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        min_amount: Decimal | None,
        max_amount: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[PaymentDTO]: ...
    async def create_payment(
        self,
        booking_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        amount: Decimal,
        currency: str,
        payment_method: str,
    ) -> PaymentDTO: ...
    async def mark_payment_succeeded(self, payment_id: UUID, paid_at: datetime) -> PaymentDTO: ...
    async def fail_payment(self, payment_id: UUID, reason: str) -> PaymentDTO: ...
    async def refund_payment(self, payment_id: UUID, reason: str | None) -> PaymentDTO: ...


class ReviewGateway(Protocol):
    async def list_teacher_reviews(
        self,
        teacher_id: UUID,
        page: int,
        page_size: int,
        min_rating: int | None,
        sort_by: str,
        sort_direction: str,
    ) -> ReviewPageDTO[ReviewDTO]: ...
    async def create_review(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        rating: int,
        comment: str | None,
    ) -> ReviewDTO: ...
    async def get_rating_stats(self, teacher_id: UUID) -> tuple[Decimal, int]: ...


class NotificationGateway(Protocol):
    async def list_notifications(
        self, user_id: UUID, status: str | None, event_type: str | None, sort_direction: str
    ) -> list[NotificationDTO]: ...
    async def create_notification(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        source_event_id: UUID | None,
    ) -> NotificationDTO: ...


class AnalyticsGateway(Protocol):
    async def get_report(self, period_from: date, period_to: date) -> AnalyticsReportDTO: ...
    async def record_booking_created(self, event_id: UUID, period_date: date) -> None: ...
    async def record_payment(
        self, event_id: UUID, teacher_id: UUID, period_date: date, amount: Decimal
    ) -> None: ...
    async def record_lesson_completed(
        self, event_id: UUID, teacher_id: UUID, period_date: date
    ) -> None: ...
    async def record_review(
        self, event_id: UUID, teacher_id: UUID, period_date: date, rating: int
    ) -> None: ...


class MockIdentityGateway:
    def __init__(self, database: Database, auth_service: AuthService) -> None:
        self.service = IdentityReadService(database)
        self.auth_service = auth_service
        self.write_service = IdentityWriteService(database)

    async def get_user(self, user_id: UUID) -> UserDTO | None:
        return await self.service.get_user(user_id)

    async def get_student(self, student_id: UUID) -> StudentDTO | None:
        return await self.service.get_student(student_id)

    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None:
        return await self.service.get_student_by_user_id(user_id)

    async def register(self, data: RegisterRequest) -> AuthResponse:
        return await self.auth_service.register(data)

    async def login(self, data: LoginRequest) -> AuthResponse:
        return await self.auth_service.login(data)

    async def refresh(self, data: RefreshRequest) -> AuthResponse:
        return await self.auth_service.refresh(data)

    async def logout(self, access_token: str, refresh_token: str) -> None:
        await self.auth_service.logout(access_token, refresh_token)

    async def update_student_profile(
        self,
        user_id: UUID,
        education_level: str | None,
        learning_goal: str | None,
        timezone: str | None,
    ) -> StudentDTO:
        return await self.write_service.update_student_profile(
            user_id, education_level, learning_goal, timezone
        )


class MockCatalogGateway:
    def __init__(self, database: Database) -> None:
        self.service = CatalogService(database)

    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None:
        return await self.service.get_teacher(teacher_id)

    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None:
        return await self.service.get_subject(subject_id)

    async def list_subjects(
        self, search: str | None, is_active: bool | None, sort_direction: str
    ) -> list[SubjectDTO]:
        return await self.service.list_subjects(search, is_active, sort_direction)

    async def list_teachers(
        self, filters: TeacherFilterDTO, page: int, page_size: int
    ) -> PageDTO[TeacherDTO]:
        return await self.service.list_teachers(filters, page, page_size)

    async def create_teacher_profile(
        self,
        user_id: UUID,
        about: str | None,
        experience_years: int,
        price_per_lesson: Decimal,
        currency: str,
        subject_ids: list[UUID],
    ) -> TeacherDTO:
        return await self.service.create_teacher_profile(
            user_id, about, experience_years, price_per_lesson, currency, subject_ids
        )

    async def update_teacher_profile(self, teacher_id: UUID, **changes) -> TeacherDTO:
        return await self.service.update_teacher_profile(teacher_id, **changes)

    async def add_teacher_subject(
        self, teacher_id: UUID, subject_id: UUID, proficiency_level: str | None
    ) -> TeacherDTO:
        return await self.service.add_teacher_subject(teacher_id, subject_id, proficiency_level)

    async def remove_teacher_subject(self, teacher_id: UUID, subject_id: UUID) -> TeacherDTO:
        return await self.service.remove_teacher_subject(teacher_id, subject_id)

    async def create_subject(
        self, name: str, description: str | None, is_active: bool
    ) -> SubjectDTO:
        return await self.service.create_subject(name, description, is_active)

    async def update_subject(self, subject_id: UUID, **changes) -> SubjectDTO:
        return await self.service.update_subject(subject_id, **changes)

    async def recalculate_rating(
        self, teacher_id: UUID, avg_rating: Decimal, reviews_count: int
    ) -> RatingDTO:
        return await self.service.recalculate_rating(teacher_id, avg_rating, reviews_count)


class MockSchedulingGateway:
    def __init__(self, database: Database) -> None:
        self.service = SchedulingService(database)

    async def get_lesson(self, lesson_id: UUID) -> LessonDTO | None:
        return await self.service.get_lesson(lesson_id)

    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlotDTO]:
        return await self.service.list_schedule(teacher_id)

    async def list_available_lessons(
        self,
        teacher_id: UUID | None,
        subject_id: UUID | None,
        start_from: datetime | None,
        end_to: datetime | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[LessonDTO]:
        return await self.service.list_available_lessons(
            teacher_id=teacher_id,
            subject_id=subject_id,
            start_from=start_from,
            end_to=end_to,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    async def create_schedule_slot(
        self, teacher_id: UUID, weekday: int, start_time: time, end_time: time
    ) -> ScheduleSlotDTO:
        return await self.service.create_schedule_slot(teacher_id, weekday, start_time, end_time)

    async def update_schedule_slot(self, slot_id: UUID, **changes) -> ScheduleSlotDTO:
        return await self.service.update_schedule_slot(slot_id, **changes)

    async def delete_schedule_slot(self, slot_id: UUID) -> bool:
        return await self.service.delete_schedule_slot(slot_id)

    async def create_lesson(
        self,
        teacher_id: UUID,
        subject_id: UUID,
        schedule_slot_id: UUID | None,
        start_at: datetime,
        duration_minutes: int,
        price: Decimal,
        currency: str,
    ) -> LessonDTO:
        return await self.service.create_lesson(
            teacher_id,
            subject_id,
            schedule_slot_id,
            start_at,
            duration_minutes,
            price,
            currency,
        )

    async def cancel_lesson(self, lesson_id: UUID, reason: str | None) -> LessonDTO:
        return await self.service.cancel_lesson(lesson_id, reason)

    async def reschedule_lesson(self, lesson_id: UUID, new_start_at: datetime) -> LessonDTO:
        return await self.service.reschedule_lesson(lesson_id, new_start_at)

    async def reserve_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self.service.reserve_lesson(lesson_id)

    async def release_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self.service.release_lesson(lesson_id)

    async def mark_lesson_booked(self, lesson_id: UUID) -> LessonDTO:
        return await self.service.mark_lesson_booked(lesson_id)

    async def complete_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self.service.complete_lesson(lesson_id)


class MockBookingGateway:
    def __init__(self, database: Database) -> None:
        self.service = BookingService(database)

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        return await self.service.get_booking(booking_id)

    async def get_booking_by_lesson(self, lesson_id: UUID) -> BookingDTO | None:
        return await self.service.get_booking_by_lesson(lesson_id)

    async def list_bookings(
        self,
        student_id: UUID,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[BookingDTO]:
        return await self.service.list_bookings(
            student_id,
            status,
            created_from,
            created_to,
            min_price,
            max_price,
            sort_by,
            sort_direction,
        )

    async def create_booking(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        subject_id: UUID,
        price: Decimal,
        currency: str,
    ) -> BookingDTO:
        return await self.service.create_booking(
            lesson_id, student_id, teacher_id, subject_id, price, currency
        )

    async def confirm_booking(self, booking_id: UUID, paid_at: datetime) -> BookingDTO:
        return await self.service.confirm_booking(booking_id, paid_at)

    async def cancel_booking(self, booking_id: UUID, reason: str | None) -> BookingDTO:
        return await self.service.cancel_booking(booking_id, reason)

    async def complete_booking(self, booking_id: UUID, completed_at: datetime) -> BookingDTO:
        return await self.service.complete_booking(booking_id, completed_at)


class MockPaymentGateway:
    def __init__(self, database: Database) -> None:
        self.service = PaymentService(database)

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        return await self.service.get_payment(payment_id)

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        return await self.service.get_payment_by_booking(booking_id)

    async def list_payments(
        self,
        student_id: UUID,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        min_amount: Decimal | None,
        max_amount: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ) -> list[PaymentDTO]:
        return await self.service.list_payments(
            student_id,
            status,
            created_from,
            created_to,
            min_amount,
            max_amount,
            sort_by,
            sort_direction,
        )

    async def create_payment(
        self,
        booking_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        amount: Decimal,
        currency: str,
        payment_method: str,
    ) -> PaymentDTO:
        return await self.service.create_payment(
            booking_id, student_id, teacher_id, amount, currency, payment_method
        )

    async def mark_payment_succeeded(self, payment_id: UUID, paid_at: datetime) -> PaymentDTO:
        return await self.service.mark_payment_succeeded(payment_id, paid_at)

    async def fail_payment(self, payment_id: UUID, reason: str) -> PaymentDTO:
        return await self.service.fail_payment(payment_id, reason)

    async def refund_payment(self, payment_id: UUID, reason: str | None) -> PaymentDTO:
        return await self.service.refund_payment(payment_id, reason)


class MockReviewGateway:
    def __init__(self, database: Database) -> None:
        self.service = ReviewService(database)

    async def list_teacher_reviews(
        self,
        teacher_id: UUID,
        page: int,
        page_size: int,
        min_rating: int | None,
        sort_by: str,
        sort_direction: str,
    ) -> ReviewPageDTO[ReviewDTO]:
        return await self.service.list_teacher_reviews(
            teacher_id, page, page_size, min_rating, sort_by, sort_direction
        )

    async def create_review(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        rating: int,
        comment: str | None,
    ) -> ReviewDTO:
        return await self.service.create_review(lesson_id, student_id, teacher_id, rating, comment)

    async def get_rating_stats(self, teacher_id: UUID) -> tuple[Decimal, int]:
        return await self.service.get_rating_stats(teacher_id)


class MockNotificationGateway:
    def __init__(self, database: Database) -> None:
        self.service = NotificationService(database)

    async def list_notifications(
        self, user_id: UUID, status: str | None, event_type: str | None, sort_direction: str
    ) -> list[NotificationDTO]:
        return await self.service.list_notifications(user_id, status, event_type, sort_direction)

    async def create_notification(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        source_event_id: UUID | None,
    ) -> NotificationDTO:
        return await self.service.create_notification(
            user_id, event_type, title, body, source_event_id
        )


class MockAnalyticsGateway:
    def __init__(self, database: Database) -> None:
        self.service = AnalyticsService(database)

    async def get_report(self, period_from: date, period_to: date) -> AnalyticsReportDTO:
        return await self.service.get_report(period_from, period_to)

    async def record_booking_created(self, event_id: UUID, period_date: date) -> None:
        await self.service.record_booking_created(event_id, period_date)

    async def record_payment(
        self, event_id: UUID, teacher_id: UUID, period_date: date, amount: Decimal
    ) -> None:
        await self.service.record_payment(event_id, teacher_id, period_date, amount)

    async def record_lesson_completed(
        self, event_id: UUID, teacher_id: UUID, period_date: date
    ) -> None:
        await self.service.record_lesson_completed(event_id, teacher_id, period_date)

    async def record_review(
        self, event_id: UUID, teacher_id: UUID, period_date: date, rating: int
    ) -> None:
        await self.service.record_review(event_id, teacher_id, period_date, rating)
