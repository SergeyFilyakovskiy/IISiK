import asyncio
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from shared.auth import CurrentUser, require_user_owner

from .auth_client import AuthClient
from .dto import (
    AuthResponse,
    BookingDTO,
    LessonDTO,
    LoginRequest,
    PageDTO,
    PaymentDTO,
    RefreshRequest,
    RegisterRequest,
    StudentDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
    UserDTO,
)
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


class BffService:
    def __init__(
        self,
        auth: AuthClient,
        identity: IdentityGateway,
        catalog: CatalogGateway,
        scheduling: SchedulingGateway,
        booking: BookingGateway,
        payment: PaymentGateway,
        review: ReviewGateway,
        notification: NotificationGateway,
        analytics: AnalyticsGateway,
    ) -> None:
        self.auth = auth
        self.identity = identity
        self.catalog = catalog
        self.scheduling = scheduling
        self.booking = booking
        self.payment = payment
        self.review = review
        self.notification = notification
        self.analytics = analytics

    async def close(self) -> None:
        await asyncio.gather(
            self.auth.close(),
            self.identity.close(),
            self.catalog.close(),
            self.scheduling.close(),
            self.booking.close(),
            self.payment.close(),
            self.review.close(),
            self.notification.close(),
            self.analytics.close(),
        )

    async def register(self, data: RegisterRequest) -> AuthResponse:
        return await self.auth.register(data)

    async def login(self, data: LoginRequest) -> AuthResponse:
        return await self.auth.login(data)

    async def refresh(self, data: RefreshRequest) -> AuthResponse:
        return await self.auth.refresh(data)

    async def logout(self, access_token: str, refresh_token: str) -> None:
        await self.auth.logout(access_token, refresh_token)

    async def update_student_profile(self, actor: CurrentUser, **changes) -> StudentDTO:
        return await self.identity.update_student_profile(actor, **changes)

    async def get_user(self, actor: CurrentUser, user_id: UUID) -> UserDTO | None:
        require_user_owner(actor, user_id)
        return await self.identity.get_user(user_id, actor)

    async def get_student(self, actor: CurrentUser, user_id: UUID) -> StudentDTO | None:
        require_user_owner(actor, user_id)
        return await self.identity.get_student_by_user_id(user_id, actor)

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
            self.get_teacher(lesson.teacher_id), self.catalog.get_subject(lesson.subject_id)
        )
        return LessonView(lesson, teacher, subject)

    async def get_booking(self, actor: CurrentUser, booking_id: UUID) -> BookingView | None:
        booking = await self.booking.get_booking(booking_id, actor)
        if booking is None:
            return None
        lesson, payment = await asyncio.gather(
            self.get_lesson(booking.lesson_id),
            self.payment.get_payment_by_booking(booking_id, actor),
        )
        return BookingView(booking, lesson, payment)

    async def list_available_lessons(self, **filters) -> list[LessonView]:
        lessons = await self.scheduling.list_available_lessons(**filters)
        items = await asyncio.gather(*(self.get_lesson(lesson.id) for lesson in lessons))
        return [item for item in items if item is not None]

    async def list_subjects(self, search: str | None, is_active: bool | None, direction: str):
        return await self.catalog.list_subjects(search, is_active, direction)

    async def list_schedule(self, teacher_id: UUID):
        return await self.scheduling.list_schedule(teacher_id)

    async def list_bookings(self, actor: CurrentUser, **filters) -> list[BookingView]:
        bookings = await self.booking.list_bookings(actor, **filters)
        items = await asyncio.gather(*(self.get_booking(actor, booking.id) for booking in bookings))
        return [item for item in items if item is not None]

    async def get_payment(self, actor: CurrentUser, payment_id: UUID):
        return await self.payment.get_payment(payment_id, actor)

    async def list_payments(self, actor: CurrentUser, **filters):
        return await self.payment.list_payments(actor, **filters)

    async def list_reviews(self, teacher_id: UUID, **values):
        return await self.review.list_teacher_reviews(teacher_id, **values)

    async def list_notifications(self, actor: CurrentUser, **filters):
        return await self.notification.list_notifications(actor, **filters)

    async def get_analytics(self, actor: CurrentUser, period_from: date, period_to: date):
        return await self.analytics.get_report(actor, period_from, period_to)

    async def create_teacher_profile(self, actor: CurrentUser, **values):
        teacher = await self.catalog.create_teacher_profile(actor, **values)
        return await self.get_teacher(teacher.id)

    async def update_teacher_profile(self, actor: CurrentUser, teacher_id: UUID, **changes):
        teacher = await self.catalog.update_teacher_profile(teacher_id, actor, **changes)
        return await self.get_teacher(teacher.id)

    async def add_teacher_subject(
        self, actor: CurrentUser, teacher_id: UUID, subject_id: UUID, level: str | None
    ):
        teacher = await self.catalog.add_teacher_subject(teacher_id, subject_id, level, actor)
        return await self.get_teacher(teacher.id)

    async def remove_teacher_subject(self, actor: CurrentUser, teacher_id: UUID, subject_id: UUID):
        teacher = await self.catalog.remove_teacher_subject(teacher_id, subject_id, actor)
        return await self.get_teacher(teacher.id)

    async def create_subject(self, actor: CurrentUser, **values):
        return await self.catalog.create_subject(actor, **values)

    async def update_subject(self, actor: CurrentUser, subject_id: UUID, **changes):
        return await self.catalog.update_subject(subject_id, actor, **changes)

    async def create_schedule_slot(self, actor: CurrentUser, **values):
        return await self.scheduling.create_schedule_slot(actor, **values)

    async def update_schedule_slot(self, actor: CurrentUser, slot_id: UUID, **changes):
        return await self.scheduling.update_schedule_slot(slot_id, actor, **changes)

    async def delete_schedule_slot(self, actor: CurrentUser, slot_id: UUID):
        return await self.scheduling.delete_schedule_slot(slot_id, actor)

    async def create_lesson(self, actor: CurrentUser, **values):
        lesson = await self.scheduling.create_lesson(actor, **values)
        return await self.get_lesson(lesson.id)

    async def reschedule_lesson(self, actor: CurrentUser, lesson_id: UUID, new_start_at):
        lesson = await self.scheduling.reschedule_lesson(lesson_id, new_start_at, actor)
        return await self.get_lesson(lesson.id)

    async def cancel_lesson(self, actor: CurrentUser, lesson_id: UUID, reason: str | None):
        await self.booking.cancel_lesson(lesson_id, reason, actor)
        return await self.get_lesson(lesson_id)

    async def book_lesson(self, actor: CurrentUser, lesson_id: UUID):
        booking = await self.booking.book_lesson(lesson_id, actor, uuid4())
        return await self.get_booking(actor, booking.id)

    async def pay_booking(self, actor: CurrentUser, booking_id: UUID, method: str):
        booking = await self.booking.pay_booking(booking_id, method, actor, uuid4())
        return await self.get_booking(actor, booking.id)

    async def cancel_booking(self, actor: CurrentUser, booking_id: UUID, reason: str | None):
        booking = await self.booking.cancel_booking(booking_id, reason, actor)
        return await self.get_booking(actor, booking.id)

    async def mark_lesson_completed(self, actor: CurrentUser, lesson_id: UUID):
        await self.booking.complete_lesson(lesson_id, actor)
        return await self.get_lesson(lesson_id)

    async def add_review(
        self, actor: CurrentUser, lesson_id: UUID, rating: int, comment: str | None
    ):
        return await self.review.create_review(actor, lesson_id, rating, comment, uuid4())
