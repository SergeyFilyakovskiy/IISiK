from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class StudentDTO:
    id: UUID
    user_id: UUID
    education_level: str | None
    learning_goal: str | None
    timezone: str | None
    status: str


@dataclass(slots=True)
class UserDTO:
    id: UUID
    email: str
    full_name: str
    role: str
    status: str
    student: StudentDTO | None


@dataclass(slots=True)
class StudentProfileInput:
    education_level: str | None = None
    learning_goal: str | None = None
    timezone: str | None = None


@dataclass(slots=True)
class RegisterRequest:
    email: str
    password: str
    full_name: str
    role: str
    student_profile: StudentProfileInput | None = None


@dataclass(slots=True)
class LoginRequest:
    email: str
    password: str


@dataclass(slots=True)
class RefreshRequest:
    refresh_token: str


@dataclass(slots=True)
class AuthResponse:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserDTO


@dataclass(slots=True)
class SubjectDTO:
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TeacherSubjectDTO:
    subject: SubjectDTO
    proficiency_level: str | None


@dataclass(slots=True)
class RatingDTO:
    teacher_id: UUID
    avg_rating: Decimal
    reviews_count: int
    updated_at: datetime


@dataclass(slots=True)
class TeacherDTO:
    id: UUID
    user_id: UUID
    about: str | None
    experience_years: int
    price_per_lesson: Decimal
    currency: str
    profile_status: str
    created_at: datetime
    updated_at: datetime
    subjects: list[TeacherSubjectDTO]
    rating: RatingDTO | None


@dataclass(slots=True)
class TeacherFilterDTO:
    subject_id: UUID | None = None
    min_rating: Decimal | None = None
    max_price: Decimal | None = None
    sort_by: str = "RATING"
    sort_direction: str = "DESC"


@dataclass(slots=True)
class PageDTO[T]:
    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(slots=True)
class ScheduleSlotDTO:
    id: UUID
    teacher_id: UUID
    weekday: int
    start_time: time
    end_time: time
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class LessonDTO:
    id: UUID
    teacher_id: UUID
    subject_id: UUID
    schedule_slot_id: UUID | None
    start_at: datetime
    duration_minutes: int
    status: str
    price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class BookingDTO:
    id: UUID
    lesson_id: UUID
    student_id: UUID
    teacher_id: UUID
    subject_id: UUID
    status: str
    price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None


@dataclass(slots=True)
class PaymentDTO:
    id: UUID
    booking_id: UUID
    student_id: UUID
    teacher_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    refunded_at: datetime | None
    failure_reason: str | None
    refund_reason: str | None


@dataclass(slots=True)
class ReviewDTO:
    id: UUID
    lesson_id: UUID
    student_id: UUID
    teacher_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class NotificationDTO:
    id: UUID
    user_id: UUID
    event_type: str
    title: str
    body: str
    status: str
    source_event_id: UUID | None
    created_at: datetime
    sent_at: datetime | None


@dataclass(slots=True)
class TeacherMetricDTO:
    teacher_id: UUID
    period_date: date
    lessons_completed: int
    revenue: Decimal
    avg_rating: Decimal
    reviews_count: int


@dataclass(slots=True)
class AnalyticsReportDTO:
    period_from: date
    period_to: date
    lessons_completed: int
    bookings_created: int
    revenue: Decimal
    avg_rating: Decimal
    teachers: list[TeacherMetricDTO]
