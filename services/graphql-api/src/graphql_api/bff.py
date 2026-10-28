import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from booking_service.schemas import BookingDTO
from catalog_service.schemas import PageDTO, SubjectDTO, TeacherDTO, TeacherFilterDTO
from identity_service.read_schemas import StudentDTO, UserDTO
from identity_service.schemas import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from payment_service.schemas import PaymentDTO
from scheduling_service.schemas import LessonDTO

from .gateways import (
    AnalyticsGateway,
    BookingGateway,
    CatalogGateway,
    IdentityGateway,
    NotificationGateway,
    PaymentGateway,
    ReviewGateway,
    SchedulingGateway,
)
from .operations import BusinessOperations


@dataclass
class TeacherView:
    teacher: TeacherDTO
    user: UserDTO | None


@dataclass
class LessonView:
    lesson: LessonDTO
    teacher: TeacherView | None
    subject: SubjectDTO | None


@dataclass
class BookingView:
    booking: BookingDTO
    lesson: LessonView | None
    payment: PaymentDTO | None


class BffService(BusinessOperations):
    def __init__(
        self,
        identity: IdentityGateway,
        catalog: CatalogGateway,
        scheduling: SchedulingGateway,
        booking: BookingGateway,
        payment: PaymentGateway,
        review: ReviewGateway,
        notification: NotificationGateway,
        analytics: AnalyticsGateway,
    ) -> None:
        self.identity = identity
        self.catalog = catalog
        self.scheduling = scheduling
        self.booking = booking
        self.payment = payment
        self.review = review
        self.notification = notification
        self.analytics = analytics

    async def register(self, data: RegisterRequest) -> AuthResponse:
        return await self.identity.register(data)

    async def login(self, data: LoginRequest) -> AuthResponse:
        return await self.identity.login(data)

    async def refresh(self, data: RefreshRequest) -> AuthResponse:
        return await self.identity.refresh(data)

    async def logout(self, access_token: str, refresh_token: str) -> None:
        await self.identity.logout(access_token, refresh_token)

    async def update_student_profile(
        self,
        user_id: UUID,
        education_level: str | None,
        learning_goal: str | None,
        timezone: str | None,
    ) -> StudentDTO:
        return await self.identity.update_student_profile(
            user_id, education_level, learning_goal, timezone
        )

    async def get_user(self, user_id: UUID) -> UserDTO | None:
        return await self.identity.get_user(user_id)

    async def get_student(self, user_id: UUID) -> StudentDTO | None:
        return await self.identity.get_student_by_user_id(user_id)

    async def get_teacher(self, teacher_id: UUID) -> TeacherView | None:
        teacher = await self.catalog.get_teacher(teacher_id)
        if teacher is None:
            return None
        user = await self.identity.get_user(teacher.user_id)
        return TeacherView(teacher, user)

    async def list_teachers(
        self, filters: TeacherFilterDTO, page: int, page_size: int
    ) -> PageDTO[TeacherView]:
        result = await self.catalog.list_teachers(filters, page, page_size)
        items = await asyncio.gather(*(self.get_teacher(teacher.id) for teacher in result.items))
        return PageDTO(
            items=[item for item in items if item is not None],
            page=result.page,
            page_size=result.page_size,
            total_items=result.total_items,
            total_pages=result.total_pages,
        )

    async def get_lesson(self, lesson_id: UUID) -> LessonView | None:
        lesson = await self.scheduling.get_lesson(lesson_id)
        if lesson is None:
            return None
        teacher, subject = await asyncio.gather(
            self.get_teacher(lesson.teacher_id),
            self.catalog.get_subject(lesson.subject_id),
        )
        return LessonView(lesson, teacher, subject)

    async def get_booking(self, booking_id: UUID) -> BookingView | None:
        booking = await self.booking.get_booking(booking_id)
        if booking is None:
            return None
        lesson, payment = await asyncio.gather(
            self.get_lesson(booking.lesson_id),
            self.payment.get_payment_by_booking(booking_id),
        )
        return BookingView(booking, lesson, payment)

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
    ) -> list[LessonView]:
        lessons = await self.scheduling.list_available_lessons(
            teacher_id,
            subject_id,
            start_from,
            end_to,
            min_price,
            max_price,
            sort_by,
            sort_direction,
        )
        items = await asyncio.gather(*(self.get_lesson(lesson.id) for lesson in lessons))
        return [item for item in items if item is not None]

    def list_subjects(self, search: str | None, is_active: bool | None, sort_direction: str):
        return self.catalog.list_subjects(search, is_active, sort_direction)

    def list_schedule(self, teacher_id: UUID):
        return self.scheduling.list_schedule(teacher_id)

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
    ) -> list[BookingView]:
        bookings = await self.booking.list_bookings(
            student_id,
            status,
            created_from,
            created_to,
            min_price,
            max_price,
            sort_by,
            sort_direction,
        )
        items = await asyncio.gather(*(self.get_booking(booking.id) for booking in bookings))
        return [item for item in items if item is not None]

    def get_payment(self, payment_id: UUID):
        return self.payment.get_payment(payment_id)

    def list_payments(
        self,
        student_id: UUID,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        min_amount: Decimal | None,
        max_amount: Decimal | None,
        sort_by: str,
        sort_direction: str,
    ):
        return self.payment.list_payments(
            student_id,
            status,
            created_from,
            created_to,
            min_amount,
            max_amount,
            sort_by,
            sort_direction,
        )

    def list_reviews(
        self,
        teacher_id: UUID,
        page: int,
        page_size: int,
        min_rating: int | None,
        sort_by: str,
        sort_direction: str,
    ):
        return self.review.list_teacher_reviews(
            teacher_id, page, page_size, min_rating, sort_by, sort_direction
        )

    def list_notifications(
        self, user_id: UUID, status: str | None, event_type: str | None, sort_direction: str
    ):
        return self.notification.list_notifications(user_id, status, event_type, sort_direction)

    def get_analytics(self, period_from: date, period_to: date):
        return self.analytics.get_report(period_from, period_to)
