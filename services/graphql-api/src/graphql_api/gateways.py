from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from analytics_service.schemas import AnalyticsReportDTO
from analytics_service.service import AnalyticsService
from booking_service.schemas import BookingDTO
from booking_service.service import BookingService
from catalog_service.schemas import (
    PageDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
)
from catalog_service.service import CatalogService
from identity_service.read_schemas import StudentDTO, UserDTO
from identity_service.read_service import IdentityReadService
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
    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None: ...


class CatalogGateway(Protocol):
    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None: ...
    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None: ...
    async def list_subjects(self) -> list[SubjectDTO]: ...
    async def list_teachers(
        self, filters: TeacherFilterDTO, page: int, page_size: int
    ) -> PageDTO[TeacherDTO]: ...


class SchedulingGateway(Protocol):
    async def get_lesson(self, lesson_id: UUID) -> LessonDTO | None: ...
    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlotDTO]: ...
    async def list_available_lessons(
        self,
        teacher_id: UUID | None,
        subject_id: UUID | None,
        start_from: datetime | None,
        end_to: datetime | None,
    ) -> list[LessonDTO]: ...


class BookingGateway(Protocol):
    async def get_booking(self, booking_id: UUID) -> BookingDTO | None: ...
    async def list_bookings(
        self, student_id: UUID, status: str | None = None
    ) -> list[BookingDTO]: ...


class PaymentGateway(Protocol):
    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None: ...
    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None: ...
    async def list_payments(self, student_id: UUID) -> list[PaymentDTO]: ...


class ReviewGateway(Protocol):
    async def list_teacher_reviews(
        self, teacher_id: UUID, page: int, page_size: int
    ) -> ReviewPageDTO[ReviewDTO]: ...


class NotificationGateway(Protocol):
    async def list_notifications(self, user_id: UUID) -> list[NotificationDTO]: ...


class AnalyticsGateway(Protocol):
    async def get_report(self, period_from: date, period_to: date) -> AnalyticsReportDTO: ...


class MockIdentityGateway:
    def __init__(self, database: Database) -> None:
        self.service = IdentityReadService(database)

    async def get_user(self, user_id: UUID) -> UserDTO | None:
        return await self.service.get_user(user_id)

    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None:
        return await self.service.get_student_by_user_id(user_id)


class MockCatalogGateway:
    def __init__(self, database: Database) -> None:
        self.service = CatalogService(database)

    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None:
        return await self.service.get_teacher(teacher_id)

    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None:
        return await self.service.get_subject(subject_id)

    async def list_subjects(self) -> list[SubjectDTO]:
        return await self.service.list_subjects()

    async def list_teachers(
        self, filters: TeacherFilterDTO, page: int, page_size: int
    ) -> PageDTO[TeacherDTO]:
        return await self.service.list_teachers(filters, page, page_size)


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
    ) -> list[LessonDTO]:
        return await self.service.list_available_lessons(teacher_id, subject_id, start_from, end_to)


class MockBookingGateway:
    def __init__(self, database: Database) -> None:
        self.service = BookingService(database)

    async def get_booking(self, booking_id: UUID) -> BookingDTO | None:
        return await self.service.get_booking(booking_id)

    async def list_bookings(self, student_id: UUID, status: str | None = None) -> list[BookingDTO]:
        return await self.service.list_bookings(student_id, status)


class MockPaymentGateway:
    def __init__(self, database: Database) -> None:
        self.service = PaymentService(database)

    async def get_payment(self, payment_id: UUID) -> PaymentDTO | None:
        return await self.service.get_payment(payment_id)

    async def get_payment_by_booking(self, booking_id: UUID) -> PaymentDTO | None:
        return await self.service.get_payment_by_booking(booking_id)

    async def list_payments(self, student_id: UUID) -> list[PaymentDTO]:
        return await self.service.list_payments(student_id)


class MockReviewGateway:
    def __init__(self, database: Database) -> None:
        self.service = ReviewService(database)

    async def list_teacher_reviews(
        self, teacher_id: UUID, page: int, page_size: int
    ) -> ReviewPageDTO[ReviewDTO]:
        return await self.service.list_teacher_reviews(teacher_id, page, page_size)


class MockNotificationGateway:
    def __init__(self, database: Database) -> None:
        self.service = NotificationService(database)

    async def list_notifications(self, user_id: UUID) -> list[NotificationDTO]:
        return await self.service.list_notifications(user_id)


class MockAnalyticsGateway:
    def __init__(self, database: Database) -> None:
        self.service = AnalyticsService(database)

    async def get_report(self, period_from: date, period_to: date) -> AnalyticsReportDTO:
        return await self.service.get_report(period_from, period_to)
