from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

import strawberry
from strawberry import Info

from catalog_service.schemas import TeacherFilterDTO

from .bff import BffService, BookingView, LessonView, TeacherView


@strawberry.enum
class Role(Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


@strawberry.enum
class LessonStatus(Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    BOOKED = "BOOKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class BookingStatus(Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class PaymentStatus(Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


@strawberry.enum
class TeacherSortField(Enum):
    RATING = "RATING"
    PRICE = "PRICE"
    POPULARITY = "POPULARITY"


@strawberry.enum
class SortDirection(Enum):
    ASC = "ASC"
    DESC = "DESC"


@strawberry.type
class Student:
    id: UUID
    user_id: UUID
    education_level: str | None
    learning_goal: str | None
    timezone: str | None
    status: str


@strawberry.type
class User:
    id: UUID
    email: str
    full_name: str
    role: Role
    status: str
    student: Student | None


@strawberry.type
class Subject:
    id: UUID
    name: str
    description: str | None
    is_active: bool


@strawberry.type
class TeacherSubject:
    subject: Subject
    proficiency_level: str | None


@strawberry.type
class Rating:
    teacher_id: UUID
    avg_rating: float
    reviews_count: int
    updated_at: datetime


@strawberry.type
class TeacherProfile:
    id: UUID
    user: User | None
    about: str | None
    experience_years: int
    price_per_lesson: float
    currency: str
    profile_status: str
    subjects: list[TeacherSubject]
    rating: Rating | None


@strawberry.type
class ScheduleSlot:
    id: UUID
    teacher_id: UUID
    weekday: int
    start_time: time
    end_time: time
    is_active: bool


@strawberry.type
class Lesson:
    id: UUID
    teacher: TeacherProfile | None
    subject: Subject | None
    schedule_slot_id: UUID | None
    start_at: datetime
    duration_minutes: int
    status: LessonStatus
    price: float
    currency: str


@strawberry.type
class Payment:
    id: UUID
    booking_id: UUID
    student_id: UUID
    teacher_id: UUID
    amount: float
    currency: str
    payment_method: str
    status: PaymentStatus
    created_at: datetime
    paid_at: datetime | None
    refunded_at: datetime | None


@strawberry.type
class Booking:
    id: UUID
    lesson: Lesson | None
    student_id: UUID
    teacher_id: UUID
    subject_id: UUID
    status: BookingStatus
    price: float
    currency: str
    created_at: datetime
    paid_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    payment: Payment | None


@strawberry.type
class Review:
    id: UUID
    lesson_id: UUID
    student_id: UUID
    teacher_id: UUID
    rating: int
    comment: str | None
    created_at: datetime


@strawberry.type
class PageInfo:
    page: int
    page_size: int
    total_items: int
    total_pages: int


@strawberry.type
class TeacherPage:
    items: list[TeacherProfile]
    page_info: PageInfo


@strawberry.type
class ReviewPage:
    items: list[Review]
    page_info: PageInfo


@strawberry.type
class Notification:
    id: UUID
    user_id: UUID
    event_type: str
    title: str
    body: str
    status: str
    source_event_id: UUID | None
    created_at: datetime
    sent_at: datetime | None


@strawberry.type
class TeacherAnalytics:
    teacher_id: UUID
    lessons_completed: int
    revenue: float
    avg_rating: float
    reviews_count: int


@strawberry.type
class AnalyticsReport:
    period_from: date
    period_to: date
    lessons_completed: int
    bookings_created: int
    revenue: float
    avg_rating: float
    teachers: list[TeacherAnalytics]


@strawberry.input
class PaginationInput:
    page: int = 1
    page_size: int = 20


@strawberry.input
class TeacherFilterInput:
    subject_id: UUID | None = None
    min_rating: float | None = None
    max_price: float | None = None
    sort_by: TeacherSortField = TeacherSortField.RATING
    sort_direction: SortDirection = SortDirection.DESC


@strawberry.input
class AnalyticsPeriodInput:
    from_date: date = strawberry.field(name="from")
    to_date: date = strawberry.field(name="to")


def map_student(dto) -> Student:
    return Student(
        id=dto.id,
        user_id=dto.user_id,
        education_level=dto.education_level,
        learning_goal=dto.learning_goal,
        timezone=dto.timezone,
        status=dto.status,
    )


def map_user(dto) -> User:
    return User(
        id=dto.id,
        email=dto.email,
        full_name=dto.full_name,
        role=Role(dto.role),
        status=dto.status,
        student=map_student(dto.student) if dto.student else None,
    )


def map_subject(dto) -> Subject:
    return Subject(id=dto.id, name=dto.name, description=dto.description, is_active=dto.is_active)


def map_teacher(view: TeacherView) -> TeacherProfile:
    teacher = view.teacher
    subjects = [
        TeacherSubject(subject=map_subject(link.subject), proficiency_level=link.proficiency_level)
        for link in teacher.subjects
    ]
    rating = None
    if teacher.rating:
        rating = Rating(
            teacher_id=teacher.rating.teacher_id,
            avg_rating=float(teacher.rating.avg_rating),
            reviews_count=teacher.rating.reviews_count,
            updated_at=teacher.rating.updated_at,
        )
    return TeacherProfile(
        id=teacher.id,
        user=map_user(view.user) if view.user else None,
        about=teacher.about,
        experience_years=teacher.experience_years,
        price_per_lesson=float(teacher.price_per_lesson),
        currency=teacher.currency,
        profile_status=teacher.profile_status,
        subjects=subjects,
        rating=rating,
    )


def map_lesson(view: LessonView) -> Lesson:
    lesson = view.lesson
    return Lesson(
        id=lesson.id,
        teacher=map_teacher(view.teacher) if view.teacher else None,
        subject=map_subject(view.subject) if view.subject else None,
        schedule_slot_id=lesson.schedule_slot_id,
        start_at=lesson.start_at,
        duration_minutes=lesson.duration_minutes,
        status=LessonStatus(lesson.status),
        price=float(lesson.price),
        currency=lesson.currency,
    )


def map_payment(dto) -> Payment:
    return Payment(
        id=dto.id,
        booking_id=dto.booking_id,
        student_id=dto.student_id,
        teacher_id=dto.teacher_id,
        amount=float(dto.amount),
        currency=dto.currency,
        payment_method=dto.payment_method,
        status=PaymentStatus(dto.status),
        created_at=dto.created_at,
        paid_at=dto.paid_at,
        refunded_at=dto.refunded_at,
    )


def map_booking(view: BookingView) -> Booking:
    booking = view.booking
    return Booking(
        id=booking.id,
        lesson=map_lesson(view.lesson) if view.lesson else None,
        student_id=booking.student_id,
        teacher_id=booking.teacher_id,
        subject_id=booking.subject_id,
        status=BookingStatus(booking.status),
        price=float(booking.price),
        currency=booking.currency,
        created_at=booking.created_at,
        paid_at=booking.paid_at,
        completed_at=booking.completed_at,
        cancelled_at=booking.cancelled_at,
        cancel_reason=booking.cancel_reason,
        payment=map_payment(view.payment) if view.payment else None,
    )


def map_review(dto) -> Review:
    return Review(
        id=dto.id,
        lesson_id=dto.lesson_id,
        student_id=dto.student_id,
        teacher_id=dto.teacher_id,
        rating=dto.rating,
        comment=dto.comment,
        created_at=dto.created_at,
    )


def page_info(page) -> PageInfo:
    return PageInfo(
        page=page.page,
        page_size=page.page_size,
        total_items=page.total_items,
        total_pages=page.total_pages,
    )


def bff(info: Info) -> BffService:
    return info.context["bff"]


@strawberry.type
class Query:
    @strawberry.field
    async def user(self, info: Info, user_id: UUID) -> User | None:
        result = await bff(info).get_user(user_id)
        return map_user(result) if result else None

    @strawberry.field
    async def student_profile(self, info: Info, user_id: UUID) -> Student | None:
        result = await bff(info).get_student(user_id)
        return map_student(result) if result else None

    @strawberry.field
    async def teacher_profile(self, info: Info, teacher_id: UUID) -> TeacherProfile | None:
        result = await bff(info).get_teacher(teacher_id)
        return map_teacher(result) if result else None

    @strawberry.field
    async def teachers(
        self,
        info: Info,
        filter: TeacherFilterInput | None = None,
        page: PaginationInput | None = None,
    ) -> TeacherPage:
        filter = filter or TeacherFilterInput()
        page = page or PaginationInput()
        filters = TeacherFilterDTO(
            subject_id=filter.subject_id,
            min_rating=Decimal(str(filter.min_rating)) if filter.min_rating is not None else None,
            max_price=Decimal(str(filter.max_price)) if filter.max_price is not None else None,
            sort_by=filter.sort_by.value,
            sort_direction=filter.sort_direction.value,
        )
        result = await bff(info).list_teachers(filters, page.page, page.page_size)
        return TeacherPage(
            items=[map_teacher(item) for item in result.items], page_info=page_info(result)
        )

    @strawberry.field
    async def subjects(self, info: Info) -> list[Subject]:
        return [map_subject(item) for item in await bff(info).list_subjects()]

    @strawberry.field
    async def teacher_schedule(self, info: Info, teacher_id: UUID) -> list[ScheduleSlot]:
        slots = await bff(info).list_schedule(teacher_id)
        return [
            ScheduleSlot(
                id=slot.id,
                teacher_id=slot.teacher_id,
                weekday=slot.weekday,
                start_time=slot.start_time,
                end_time=slot.end_time,
                is_active=slot.is_active,
            )
            for slot in slots
        ]

    @strawberry.field
    async def available_lessons(
        self,
        info: Info,
        teacher_id: UUID | None = None,
        subject_id: UUID | None = None,
        from_datetime: Annotated[datetime | None, strawberry.argument(name="from")] = None,
        to: datetime | None = None,
    ) -> list[Lesson]:
        lessons = await bff(info).list_available_lessons(teacher_id, subject_id, from_datetime, to)
        return [map_lesson(lesson) for lesson in lessons]

    @strawberry.field
    async def lesson(self, info: Info, lesson_id: UUID) -> Lesson | None:
        result = await bff(info).get_lesson(lesson_id)
        return map_lesson(result) if result else None

    @strawberry.field
    async def booking(self, info: Info, booking_id: UUID) -> Booking | None:
        result = await bff(info).get_booking(booking_id)
        return map_booking(result) if result else None

    @strawberry.field
    async def bookings(
        self, info: Info, student_id: UUID, status: BookingStatus | None = None
    ) -> list[Booking]:
        result = await bff(info).list_bookings(student_id, status.value if status else None)
        return [map_booking(booking) for booking in result]

    @strawberry.field
    async def payment(self, info: Info, payment_id: UUID) -> Payment | None:
        result = await bff(info).get_payment(payment_id)
        return map_payment(result) if result else None

    @strawberry.field
    async def payments(self, info: Info, student_id: UUID) -> list[Payment]:
        return [map_payment(item) for item in await bff(info).list_payments(student_id)]

    @strawberry.field
    async def teacher_reviews(
        self,
        info: Info,
        teacher_id: UUID,
        page: PaginationInput | None = None,
    ) -> ReviewPage:
        page = page or PaginationInput()
        result = await bff(info).list_reviews(teacher_id, page.page, page.page_size)
        return ReviewPage(
            items=[map_review(item) for item in result.items], page_info=page_info(result)
        )

    @strawberry.field
    async def notifications(self, info: Info, user_id: UUID) -> list[Notification]:
        notifications = await bff(info).list_notifications(user_id)
        return [
            Notification(
                id=item.id,
                user_id=item.user_id,
                event_type=item.event_type,
                title=item.title,
                body=item.body,
                status=item.status,
                source_event_id=item.source_event_id,
                created_at=item.created_at,
                sent_at=item.sent_at,
            )
            for item in notifications
        ]

    @strawberry.field
    async def admin_analytics(self, info: Info, period: AnalyticsPeriodInput) -> AnalyticsReport:
        result = await bff(info).get_analytics(period.from_date, period.to_date)
        return AnalyticsReport(
            period_from=result.period_from,
            period_to=result.period_to,
            lessons_completed=result.lessons_completed,
            bookings_created=result.bookings_created,
            revenue=float(result.revenue),
            avg_rating=float(result.avg_rating),
            teachers=[
                TeacherAnalytics(
                    teacher_id=item.teacher_id,
                    lessons_completed=item.lessons_completed,
                    revenue=float(item.revenue),
                    avg_rating=float(item.avg_rating),
                    reviews_count=item.reviews_count,
                )
                for item in result.teachers
            ],
        )


schema = strawberry.Schema(query=Query)
