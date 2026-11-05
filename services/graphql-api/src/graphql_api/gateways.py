from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from analytics.v1 import analytics_pb2, analytics_pb2_grpc
from booking.v1 import booking_pb2, booking_pb2_grpc
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from identity.v1 import identity_pb2, identity_pb2_grpc
from notification.v1 import notification_pb2, notification_pb2_grpc
from payment.v1 import payment_pb2, payment_pb2_grpc
from review.v1 import review_pb2, review_pb2_grpc
from scheduling.v1 import scheduling_pb2, scheduling_pb2_grpc

from shared.auth import CurrentUser
from shared.grpc import call_with_policy, create_channel

from .dto import (
    AnalyticsReportDTO,
    BookingDTO,
    LessonDTO,
    NotificationDTO,
    PageDTO,
    PaymentDTO,
    RatingDTO,
    ReviewDTO,
    ScheduleSlotDTO,
    StudentDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
    TeacherMetricDTO,
    TeacherSubjectDTO,
    UserDTO,
)


def optional_datetime(message, field: str) -> datetime | None:
    return datetime.fromisoformat(getattr(message, field)) if message.HasField(field) else None


def user_from_proto(message) -> UserDTO:
    student = message.student if message.HasField("student") else None
    return UserDTO(
        id=UUID(message.id),
        email=message.email,
        full_name=message.full_name,
        role=identity_pb2.Role.Name(message.role),
        status=message.status,
        student=student_from_proto(student) if student else None,
    )


def student_from_proto(message) -> StudentDTO:
    return StudentDTO(
        id=UUID(message.id),
        user_id=UUID(message.user_id),
        education_level=message.education_level if message.HasField("education_level") else None,
        learning_goal=message.learning_goal if message.HasField("learning_goal") else None,
        timezone=message.timezone if message.HasField("timezone") else None,
        status=message.status,
    )


def subject_from_proto(message) -> SubjectDTO:
    return SubjectDTO(
        id=UUID(message.id),
        name=message.name,
        description=message.description if message.HasField("description") else None,
        is_active=message.is_active,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
    )


def teacher_from_proto(message) -> TeacherDTO:
    rating = message.rating if message.HasField("rating") else None
    return TeacherDTO(
        id=UUID(message.id),
        user_id=UUID(message.user_id),
        about=message.about if message.HasField("about") else None,
        experience_years=message.experience_years,
        price_per_lesson=Decimal(message.price_per_lesson),
        currency=message.currency,
        profile_status=message.profile_status,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
        subjects=[
            TeacherSubjectDTO(
                subject=subject_from_proto(link.subject),
                proficiency_level=link.proficiency_level
                if link.HasField("proficiency_level")
                else None,
            )
            for link in message.subjects
        ],
        rating=RatingDTO(
            teacher_id=UUID(rating.teacher_id),
            avg_rating=Decimal(rating.avg_rating),
            reviews_count=rating.reviews_count,
            updated_at=datetime.fromisoformat(rating.updated_at),
        )
        if rating
        else None,
    )


def slot_from_proto(message) -> ScheduleSlotDTO:
    return ScheduleSlotDTO(
        id=UUID(message.id),
        teacher_id=UUID(message.teacher_id),
        weekday=message.weekday,
        start_time=time.fromisoformat(message.start_time),
        end_time=time.fromisoformat(message.end_time),
        is_active=message.is_active,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
    )


def lesson_from_proto(message) -> LessonDTO:
    return LessonDTO(
        id=UUID(message.id),
        teacher_id=UUID(message.teacher_id),
        subject_id=UUID(message.subject_id),
        schedule_slot_id=UUID(message.schedule_slot_id)
        if message.HasField("schedule_slot_id")
        else None,
        start_at=datetime.fromisoformat(message.start_at),
        duration_minutes=message.duration_minutes,
        status=message.status,
        price=Decimal(message.price),
        currency=message.currency,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
    )


def booking_from_proto(message) -> BookingDTO:
    return BookingDTO(
        id=UUID(message.id),
        lesson_id=UUID(message.lesson_id),
        student_id=UUID(message.student_id),
        teacher_id=UUID(message.teacher_id),
        subject_id=UUID(message.subject_id),
        status=message.status,
        price=Decimal(message.price),
        currency=message.currency,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
        paid_at=optional_datetime(message, "paid_at"),
        completed_at=optional_datetime(message, "completed_at"),
        cancelled_at=optional_datetime(message, "cancelled_at"),
        cancel_reason=message.cancel_reason if message.HasField("cancel_reason") else None,
    )


def payment_from_proto(message) -> PaymentDTO:
    return PaymentDTO(
        id=UUID(message.id),
        booking_id=UUID(message.booking_id),
        student_id=UUID(message.student_id),
        teacher_id=UUID(message.teacher_id),
        amount=Decimal(message.amount),
        currency=message.currency,
        payment_method=message.payment_method,
        status=message.status,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
        paid_at=optional_datetime(message, "paid_at"),
        refunded_at=optional_datetime(message, "refunded_at"),
        failure_reason=message.failure_reason if message.HasField("failure_reason") else None,
        refund_reason=message.refund_reason if message.HasField("refund_reason") else None,
    )


def review_from_proto(message) -> ReviewDTO:
    return ReviewDTO(
        id=UUID(message.id),
        lesson_id=UUID(message.lesson_id),
        student_id=UUID(message.student_id),
        teacher_id=UUID(message.teacher_id),
        rating=message.rating,
        comment=message.comment if message.HasField("comment") else None,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
    )


class GrpcGateway:
    def __init__(self, address: str, timeout: float) -> None:
        self.channel = create_channel(address)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def call(self, method, request, actor: CurrentUser | None = None, retry: bool = False):
        return await call_with_policy(
            method,
            request,
            timeout=self.timeout,
            retry=retry,
            principal=actor,
        )


class IdentityGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = identity_pb2_grpc.IdentityServiceStub(self.channel)

    async def get_user(self, user_id: UUID, actor: CurrentUser | None = None) -> UserDTO | None:
        response = await self.call(
            self.stub.GetUserById,
            identity_pb2.GetUserByIdRequest(user_id=str(user_id)),
            actor,
            True,
        )
        return user_from_proto(response.user) if response.HasField("user") else None

    async def get_student(self, student_id: UUID, actor: CurrentUser) -> StudentDTO | None:
        response = await self.call(
            self.stub.GetStudent,
            identity_pb2.GetStudentRequest(student_id=str(student_id)),
            actor,
            True,
        )
        return student_from_proto(response.student) if response.HasField("student") else None

    async def get_student_by_user_id(self, user_id: UUID, actor: CurrentUser) -> StudentDTO | None:
        response = await self.call(
            self.stub.GetStudentByUserId,
            identity_pb2.GetStudentByUserIdRequest(user_id=str(user_id)),
            actor,
            True,
        )
        return student_from_proto(response.student) if response.HasField("student") else None

    async def update_student_profile(self, actor: CurrentUser, **changes) -> StudentDTO:
        request = identity_pb2.UpdateStudentProfileRequest()
        for key, value in changes.items():
            if value is not None:
                setattr(request, key, value)
        response = await self.call(self.stub.UpdateStudentProfile, request, actor)
        return student_from_proto(response)


class CatalogGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = catalog_pb2_grpc.CatalogServiceStub(self.channel)

    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None:
        response = await self.call(
            self.stub.GetTeacher,
            catalog_pb2.GetTeacherRequest(teacher_id=str(teacher_id)),
            retry=True,
        )
        return teacher_from_proto(response.teacher) if response.HasField("teacher") else None

    async def get_teacher_by_user_id(self, user_id: UUID) -> TeacherDTO | None:
        response = await self.call(
            self.stub.GetTeacherByUserId,
            catalog_pb2.GetTeacherByUserIdRequest(user_id=str(user_id)),
            retry=True,
        )
        return teacher_from_proto(response.teacher) if response.HasField("teacher") else None

    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None:
        response = await self.call(
            self.stub.GetSubject,
            catalog_pb2.GetSubjectRequest(subject_id=str(subject_id)),
            retry=True,
        )
        return subject_from_proto(response.subject) if response.HasField("subject") else None

    async def list_subjects(self, search: str | None, is_active: bool | None, direction: str):
        request = catalog_pb2.ListSubjectsRequest(sort_direction=direction)
        if search is not None:
            request.search = search
        if is_active is not None:
            request.is_active = is_active
        response = await self.call(self.stub.ListSubjects, request, retry=True)
        return [subject_from_proto(item) for item in response.items]

    async def list_teachers(self, filters: TeacherFilterDTO, page: int, page_size: int):
        request = catalog_pb2.ListTeachersRequest(
            sort_by=filters.sort_by,
            sort_direction=filters.sort_direction,
            page=page,
            page_size=page_size,
        )
        for field in ("subject_id", "min_rating", "max_price"):
            value = getattr(filters, field)
            if value is not None:
                setattr(request, field, str(value))
        response = await self.call(self.stub.ListTeachers, request, retry=True)
        return PageDTO(
            items=[teacher_from_proto(item) for item in response.items],
            page=response.page_info.page,
            page_size=response.page_info.page_size,
            total_items=response.page_info.total_items,
            total_pages=response.page_info.total_pages,
        )

    async def create_teacher_profile(self, actor: CurrentUser, **values):
        request = catalog_pb2.CreateTeacherProfileRequest(
            experience_years=values["experience_years"],
            price_per_lesson=str(values["price_per_lesson"]),
            currency=values["currency"],
            subject_ids=[str(item) for item in values["subject_ids"]],
        )
        if values["about"] is not None:
            request.about = values["about"]
        return teacher_from_proto(await self.call(self.stub.CreateTeacherProfile, request, actor))

    async def update_teacher_profile(self, teacher_id: UUID, actor: CurrentUser, **changes):
        request = catalog_pb2.UpdateTeacherProfileRequest(teacher_id=str(teacher_id))
        for key, value in changes.items():
            if value is not None:
                setattr(request, key, str(value) if key == "price_per_lesson" else value)
        return teacher_from_proto(await self.call(self.stub.UpdateTeacherProfile, request, actor))

    async def add_teacher_subject(
        self, teacher_id: UUID, subject_id: UUID, level: str | None, actor
    ):
        request = catalog_pb2.TeacherSubjectRequest(
            teacher_id=str(teacher_id), subject_id=str(subject_id)
        )
        if level is not None:
            request.proficiency_level = level
        return teacher_from_proto(await self.call(self.stub.AddTeacherSubject, request, actor))

    async def remove_teacher_subject(self, teacher_id: UUID, subject_id: UUID, actor):
        request = catalog_pb2.RemoveTeacherSubjectRequest(
            teacher_id=str(teacher_id), subject_id=str(subject_id)
        )
        return teacher_from_proto(await self.call(self.stub.RemoveTeacherSubject, request, actor))

    async def create_subject(
        self, actor: CurrentUser, name: str, description: str | None, active: bool
    ):
        request = catalog_pb2.CreateSubjectRequest(name=name, is_active=active)
        if description is not None:
            request.description = description
        return subject_from_proto(await self.call(self.stub.CreateSubject, request, actor))

    async def update_subject(self, subject_id: UUID, actor: CurrentUser, **changes):
        request = catalog_pb2.UpdateSubjectRequest(subject_id=str(subject_id))
        for key, value in changes.items():
            if value is not None:
                setattr(request, key, value)
        return subject_from_proto(await self.call(self.stub.UpdateSubject, request, actor))


class SchedulingGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = scheduling_pb2_grpc.SchedulingServiceStub(self.channel)

    async def get_lesson(self, lesson_id: UUID) -> LessonDTO | None:
        response = await self.call(
            self.stub.GetLesson,
            scheduling_pb2.GetLessonRequest(lesson_id=str(lesson_id)),
            retry=True,
        )
        return lesson_from_proto(response.lesson) if response.HasField("lesson") else None

    async def list_schedule(self, teacher_id: UUID):
        response = await self.call(
            self.stub.ListSchedule,
            scheduling_pb2.ListScheduleRequest(teacher_id=str(teacher_id)),
            retry=True,
        )
        return [slot_from_proto(item) for item in response.items]

    async def list_available_lessons(self, **filters):
        request = scheduling_pb2.ListAvailableLessonsRequest(
            sort_by=filters["sort_by"], sort_direction=filters["sort_direction"]
        )
        for key in ("teacher_id", "subject_id", "start_from", "end_to", "min_price", "max_price"):
            value = filters.get(key)
            if value is not None:
                setattr(
                    request, key, value.isoformat() if isinstance(value, datetime) else str(value)
                )
        response = await self.call(self.stub.ListAvailableLessons, request, retry=True)
        return [lesson_from_proto(item) for item in response.items]

    async def create_schedule_slot(self, actor: CurrentUser, **values):
        request = scheduling_pb2.CreateScheduleSlotRequest(
            teacher_id=str(values["teacher_id"]),
            weekday=values["weekday"],
            start_time=values["start_time"].isoformat(),
            end_time=values["end_time"].isoformat(),
        )
        return slot_from_proto(await self.call(self.stub.CreateScheduleSlot, request, actor))

    async def update_schedule_slot(self, slot_id: UUID, actor: CurrentUser, **changes):
        request = scheduling_pb2.UpdateScheduleSlotRequest(slot_id=str(slot_id))
        for key, value in changes.items():
            if value is not None:
                setattr(request, key, value.isoformat() if isinstance(value, time) else value)
        return slot_from_proto(await self.call(self.stub.UpdateScheduleSlot, request, actor))

    async def delete_schedule_slot(self, slot_id: UUID, actor: CurrentUser):
        response = await self.call(
            self.stub.DeleteScheduleSlot,
            scheduling_pb2.DeleteScheduleSlotRequest(slot_id=str(slot_id)),
            actor,
        )
        return response.deleted

    async def create_lesson(self, actor: CurrentUser, **values):
        request = scheduling_pb2.PublishLessonRequest(
            teacher_id=str(values["teacher_id"]),
            subject_id=str(values["subject_id"]),
            start_at=values["start_at"].isoformat(),
            duration_minutes=values["duration_minutes"],
        )
        if values["schedule_slot_id"] is not None:
            request.schedule_slot_id = str(values["schedule_slot_id"])
        return lesson_from_proto(await self.call(self.stub.PublishLesson, request, actor))

    async def reschedule_lesson(self, lesson_id: UUID, new_start_at: datetime, actor: CurrentUser):
        request = scheduling_pb2.RescheduleLessonRequest(
            lesson_id=str(lesson_id), new_start_at=new_start_at.isoformat()
        )
        return lesson_from_proto(await self.call(self.stub.RescheduleLesson, request, actor))


class BookingGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = booking_pb2_grpc.BookingServiceStub(self.channel)

    async def get_booking(self, booking_id: UUID, actor: CurrentUser) -> BookingDTO | None:
        response = await self.call(
            self.stub.GetBooking,
            booking_pb2.GetBookingRequest(booking_id=str(booking_id)),
            actor,
            True,
        )
        return booking_from_proto(response.booking) if response.HasField("booking") else None

    async def list_bookings(self, actor: CurrentUser, **filters):
        request = booking_pb2.ListBookingsRequest(
            sort_by=filters["sort_by"], sort_direction=filters["sort_direction"]
        )
        for key in ("student_id", "status", "created_from", "created_to", "min_price", "max_price"):
            value = filters.get(key)
            if value is not None:
                setattr(
                    request, key, value.isoformat() if isinstance(value, datetime) else str(value)
                )
        response = await self.call(self.stub.ListBookings, request, actor, True)
        return [booking_from_proto(item) for item in response.items]

    async def book_lesson(self, lesson_id: UUID, actor: CurrentUser, key: UUID):
        request = booking_pb2.BookLessonRequest(lesson_id=str(lesson_id), idempotency_key=str(key))
        return booking_from_proto(await self.call(self.stub.BookLesson, request, actor))

    async def pay_booking(self, booking_id: UUID, method: str, actor: CurrentUser, key: UUID):
        request = booking_pb2.PayBookingRequest(
            booking_id=str(booking_id), payment_method=method, idempotency_key=str(key)
        )
        return booking_from_proto(await self.call(self.stub.PayBooking, request, actor))

    async def cancel_booking(self, booking_id: UUID, reason: str | None, actor: CurrentUser):
        request = booking_pb2.CancelBookingRequest(booking_id=str(booking_id))
        if reason is not None:
            request.reason = reason
        return booking_from_proto(await self.call(self.stub.CancelBooking, request, actor))

    async def cancel_lesson(self, lesson_id: UUID, reason: str | None, actor: CurrentUser):
        request = booking_pb2.CancelLessonRequest(lesson_id=str(lesson_id))
        if reason is not None:
            request.reason = reason
        await self.call(self.stub.CancelLesson, request, actor)

    async def complete_lesson(self, lesson_id: UUID, actor: CurrentUser):
        request = booking_pb2.CompleteLessonRequest(lesson_id=str(lesson_id))
        return booking_from_proto(await self.call(self.stub.CompleteLesson, request, actor))


class PaymentGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = payment_pb2_grpc.PaymentServiceStub(self.channel)

    async def get_payment(self, payment_id: UUID, actor: CurrentUser) -> PaymentDTO | None:
        response = await self.call(
            self.stub.GetPayment,
            payment_pb2.GetPaymentRequest(payment_id=str(payment_id)),
            actor,
            True,
        )
        return payment_from_proto(response.payment) if response.HasField("payment") else None

    async def get_payment_by_booking(
        self, booking_id: UUID, actor: CurrentUser
    ) -> PaymentDTO | None:
        response = await self.call(
            self.stub.GetPaymentByBooking,
            payment_pb2.GetPaymentByBookingRequest(booking_id=str(booking_id)),
            actor,
            True,
        )
        return payment_from_proto(response.payment) if response.HasField("payment") else None

    async def list_payments(self, actor: CurrentUser, **filters):
        request = payment_pb2.ListPaymentsRequest(
            sort_by=filters["sort_by"], sort_direction=filters["sort_direction"]
        )
        for key in (
            "student_id",
            "status",
            "created_from",
            "created_to",
            "min_amount",
            "max_amount",
        ):
            value = filters.get(key)
            if value is not None:
                setattr(
                    request, key, value.isoformat() if isinstance(value, datetime) else str(value)
                )
        response = await self.call(self.stub.ListPayments, request, actor, True)
        return [payment_from_proto(item) for item in response.items]


class ReviewGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = review_pb2_grpc.ReviewServiceStub(self.channel)

    async def list_teacher_reviews(self, teacher_id: UUID, **values):
        request = review_pb2.ListTeacherReviewsRequest(
            teacher_id=str(teacher_id),
            page=values["page"],
            page_size=values["page_size"],
            sort_by=values["sort_by"],
            sort_direction=values["sort_direction"],
        )
        if values["min_rating"] is not None:
            request.min_rating = values["min_rating"]
        response = await self.call(self.stub.ListTeacherReviews, request, retry=True)
        return PageDTO(
            items=[review_from_proto(item) for item in response.items],
            page=response.page_info.page,
            page_size=response.page_info.page_size,
            total_items=response.page_info.total_items,
            total_pages=response.page_info.total_pages,
        )

    async def create_review(
        self, actor: CurrentUser, lesson_id: UUID, rating: int, comment: str | None, key: UUID
    ):
        request = review_pb2.CreateReviewRequest(
            lesson_id=str(lesson_id), rating=rating, idempotency_key=str(key)
        )
        if comment is not None:
            request.comment = comment
        return review_from_proto(await self.call(self.stub.CreateReview, request, actor))


class NotificationGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = notification_pb2_grpc.NotificationServiceStub(self.channel)

    async def list_notifications(self, actor: CurrentUser, **filters):
        request = notification_pb2.ListNotificationsRequest(
            sort_direction=filters["sort_direction"]
        )
        for key in ("user_id", "status", "event_type"):
            value = filters.get(key)
            if value is not None:
                setattr(request, key, str(value))
        response = await self.call(self.stub.ListNotifications, request, actor, True)
        return [
            NotificationDTO(
                id=UUID(item.id),
                user_id=UUID(item.user_id),
                event_type=item.event_type,
                title=item.title,
                body=item.body,
                status=item.status,
                source_event_id=UUID(item.source_event_id)
                if item.HasField("source_event_id")
                else None,
                created_at=datetime.fromisoformat(item.created_at),
                sent_at=optional_datetime(item, "sent_at"),
            )
            for item in response.items
        ]


class AnalyticsGateway(GrpcGateway):
    def __init__(self, address: str, timeout: float) -> None:
        super().__init__(address, timeout)
        self.stub = analytics_pb2_grpc.AnalyticsServiceStub(self.channel)

    async def get_report(self, actor: CurrentUser, period_from: date, period_to: date):
        response = await self.call(
            self.stub.GetReport,
            analytics_pb2.GetReportRequest(
                period_from=period_from.isoformat(), period_to=period_to.isoformat()
            ),
            actor,
            True,
        )
        return AnalyticsReportDTO(
            period_from=date.fromisoformat(response.period_from),
            period_to=date.fromisoformat(response.period_to),
            lessons_completed=response.lessons_completed,
            bookings_created=response.bookings_created,
            revenue=Decimal(response.revenue),
            avg_rating=Decimal(response.avg_rating),
            teachers=[
                TeacherMetricDTO(
                    teacher_id=UUID(item.teacher_id),
                    period_date=date.fromisoformat(item.period_date),
                    lessons_completed=item.lessons_completed,
                    revenue=Decimal(item.revenue),
                    avg_rating=Decimal(item.avg_rating),
                    reviews_count=item.reviews_count,
                )
                for item in response.teachers
            ],
        )
