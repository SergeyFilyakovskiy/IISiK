from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

import strawberry
from strawberry import Info

from shared.auth import Role as ActorRole

from .bff import BffService
from .context import actor
from .dto import LoginRequest, RefreshRequest, RegisterRequest, StudentProfileInput
from .schema import (
    Booking,
    Lesson,
    Review,
    Role,
    ScheduleSlot,
    Student,
    Subject,
    TeacherProfile,
    User,
    map_booking,
    map_lesson,
    map_review,
    map_schedule_slot,
    map_student,
    map_subject,
    map_teacher,
    map_user,
)


@strawberry.type
class AuthPayload:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: User


@strawberry.input
class RegisterStudentProfileInput:
    education_level: str | None = None
    learning_goal: str | None = None
    timezone: str | None = None


@strawberry.input
class RegisterUserInput:
    email: str
    password: str
    full_name: str
    role: Role
    student_profile: RegisterStudentProfileInput | None = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class RefreshTokenInput:
    refresh_token: str


@strawberry.input
class LogoutInput:
    refresh_token: str


@strawberry.input
class UpdateStudentProfileInput:
    education_level: str | None = None
    learning_goal: str | None = None
    timezone: str | None = None


@strawberry.input
class CreateTeacherProfileInput:
    experience_years: int
    price_per_lesson: float
    currency: str
    subject_ids: list[UUID]
    about: str | None = None


@strawberry.input
class UpdateTeacherProfileInput:
    teacher_id: UUID
    about: str | None = None
    experience_years: int | None = None
    price_per_lesson: float | None = None
    currency: str | None = None
    profile_status: str | None = None


@strawberry.input
class TeacherSubjectInput:
    teacher_id: UUID
    subject_id: UUID
    proficiency_level: str | None = None


@strawberry.input
class RemoveTeacherSubjectInput:
    teacher_id: UUID
    subject_id: UUID


@strawberry.input
class CreateSubjectInput:
    name: str
    description: str | None = None
    is_active: bool = True


@strawberry.input
class UpdateSubjectInput:
    subject_id: UUID
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


@strawberry.input
class CreateScheduleSlotInput:
    teacher_id: UUID
    weekday: int
    start_time: time
    end_time: time


@strawberry.input
class UpdateScheduleSlotInput:
    slot_id: UUID
    weekday: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


@strawberry.input
class DeleteScheduleSlotInput:
    slot_id: UUID


@strawberry.input
class PublishLessonInput:
    teacher_id: UUID
    subject_id: UUID
    start_at: datetime
    duration_minutes: int
    schedule_slot_id: UUID | None = None


@strawberry.input
class CancelLessonInput:
    lesson_id: UUID
    reason: str | None = None


@strawberry.input
class RescheduleLessonInput:
    lesson_id: UUID
    new_start_at: datetime


@strawberry.input
class BookLessonInput:
    lesson_id: UUID


@strawberry.input
class PayBookingInput:
    booking_id: UUID
    payment_method: str


@strawberry.input
class CancelBookingInput:
    booking_id: UUID
    reason: str | None = None


@strawberry.input
class CompleteLessonInput:
    lesson_id: UUID


@strawberry.input
class LeaveReviewInput:
    lesson_id: UUID
    rating: int
    comment: str | None = None


def bff(info: Info) -> BffService:
    return info.context["bff"]


def auth_payload(response) -> AuthPayload:
    return AuthPayload(
        access_token=response.access_token,
        refresh_token=response.refresh_token,
        token_type=response.token_type,
        expires_in=response.expires_in,
        user=map_user(response.user),
    )


@strawberry.type
class Mutation:
    @strawberry.field
    async def register_user(self, info: Info, input: RegisterUserInput) -> AuthPayload:
        response = await bff(info).register(
            RegisterRequest(
                email=input.email,
                password=input.password,
                full_name=input.full_name,
                role=input.role.value,
                student_profile=StudentProfileInput(
                    education_level=input.student_profile.education_level,
                    learning_goal=input.student_profile.learning_goal,
                    timezone=input.student_profile.timezone,
                )
                if input.student_profile
                else None,
            )
        )
        return auth_payload(response)

    @strawberry.field
    async def login_user(self, info: Info, input: LoginInput) -> AuthPayload:
        response = await bff(info).login(LoginRequest(input.email, input.password))
        return auth_payload(response)

    @strawberry.field
    async def refresh_token(self, info: Info, input: RefreshTokenInput) -> AuthPayload:
        response = await bff(info).refresh(RefreshRequest(input.refresh_token))
        return auth_payload(response)

    @strawberry.field
    async def logout(self, info: Info, input: LogoutInput) -> bool:
        request_auth = info.context["auth"]
        await request_auth.current_user()
        await bff(info).logout(request_auth.access_token, input.refresh_token)
        return True

    @strawberry.field
    async def update_student_profile(self, info: Info, input: UpdateStudentProfileInput) -> Student:
        student = await bff(info).update_student_profile(
            await actor(info, ActorRole.STUDENT),
            education_level=input.education_level,
            learning_goal=input.learning_goal,
            timezone=input.timezone,
        )
        return map_student(student)

    @strawberry.field
    async def create_teacher_profile(
        self, info: Info, input: CreateTeacherProfileInput
    ) -> TeacherProfile:
        teacher = await bff(info).create_teacher_profile(
            await actor(info, ActorRole.TEACHER),
            about=input.about,
            experience_years=input.experience_years,
            price_per_lesson=Decimal(str(input.price_per_lesson)),
            currency=input.currency,
            subject_ids=input.subject_ids,
        )
        return map_teacher(teacher)

    @strawberry.field
    async def update_teacher_profile(
        self, info: Info, input: UpdateTeacherProfileInput
    ) -> TeacherProfile:
        changes = {
            key: value
            for key, value in {
                "about": input.about,
                "experience_years": input.experience_years,
                "price_per_lesson": Decimal(str(input.price_per_lesson))
                if input.price_per_lesson is not None
                else None,
                "currency": input.currency,
                "profile_status": input.profile_status,
            }.items()
            if value is not None
        }
        teacher = await bff(info).update_teacher_profile(
            await actor(info, ActorRole.TEACHER), input.teacher_id, **changes
        )
        return map_teacher(teacher)

    @strawberry.field
    async def add_teacher_subject(self, info: Info, input: TeacherSubjectInput) -> TeacherProfile:
        teacher = await bff(info).add_teacher_subject(
            await actor(info, ActorRole.TEACHER),
            input.teacher_id,
            input.subject_id,
            input.proficiency_level,
        )
        return map_teacher(teacher)

    @strawberry.field
    async def remove_teacher_subject(
        self, info: Info, input: RemoveTeacherSubjectInput
    ) -> TeacherProfile:
        teacher = await bff(info).remove_teacher_subject(
            await actor(info, ActorRole.TEACHER), input.teacher_id, input.subject_id
        )
        return map_teacher(teacher)

    @strawberry.field
    async def create_subject(self, info: Info, input: CreateSubjectInput) -> Subject:
        subject = await bff(info).create_subject(
            await actor(info, ActorRole.ADMIN),
            name=input.name,
            description=input.description,
            active=input.is_active,
        )
        return map_subject(subject)

    @strawberry.field
    async def update_subject(self, info: Info, input: UpdateSubjectInput) -> Subject:
        changes = {
            key: value
            for key, value in {
                "name": input.name,
                "description": input.description,
                "is_active": input.is_active,
            }.items()
            if value is not None
        }
        subject = await bff(info).update_subject(
            await actor(info, ActorRole.ADMIN), input.subject_id, **changes
        )
        return map_subject(subject)

    @strawberry.field
    async def create_schedule_slot(
        self, info: Info, input: CreateScheduleSlotInput
    ) -> ScheduleSlot:
        slot = await bff(info).create_schedule_slot(
            await actor(info, ActorRole.TEACHER),
            teacher_id=input.teacher_id,
            weekday=input.weekday,
            start_time=input.start_time,
            end_time=input.end_time,
        )
        return map_schedule_slot(slot)

    @strawberry.field
    async def update_schedule_slot(
        self, info: Info, input: UpdateScheduleSlotInput
    ) -> ScheduleSlot:
        changes = {
            key: value
            for key, value in {
                "weekday": input.weekday,
                "start_time": input.start_time,
                "end_time": input.end_time,
                "is_active": input.is_active,
            }.items()
            if value is not None
        }
        slot = await bff(info).update_schedule_slot(
            await actor(info, ActorRole.TEACHER), input.slot_id, **changes
        )
        return map_schedule_slot(slot)

    @strawberry.field
    async def delete_schedule_slot(self, info: Info, input: DeleteScheduleSlotInput) -> bool:
        return await bff(info).delete_schedule_slot(
            await actor(info, ActorRole.TEACHER), input.slot_id
        )

    @strawberry.field
    async def publish_lesson(self, info: Info, input: PublishLessonInput) -> Lesson:
        lesson = await bff(info).create_lesson(
            await actor(info, ActorRole.TEACHER),
            teacher_id=input.teacher_id,
            subject_id=input.subject_id,
            schedule_slot_id=input.schedule_slot_id,
            start_at=input.start_at,
            duration_minutes=input.duration_minutes,
        )
        return map_lesson(lesson)

    @strawberry.field
    async def cancel_lesson(self, info: Info, input: CancelLessonInput) -> Lesson:
        lesson = await bff(info).cancel_lesson(
            await actor(info, ActorRole.TEACHER), input.lesson_id, input.reason
        )
        return map_lesson(lesson)

    @strawberry.field
    async def reschedule_lesson(self, info: Info, input: RescheduleLessonInput) -> Lesson:
        lesson = await bff(info).reschedule_lesson(
            await actor(info, ActorRole.TEACHER), input.lesson_id, input.new_start_at
        )
        return map_lesson(lesson)

    @strawberry.field
    async def book_lesson(self, info: Info, input: BookLessonInput) -> Booking:
        booking = await bff(info).book_lesson(await actor(info, ActorRole.STUDENT), input.lesson_id)
        return map_booking(booking)

    @strawberry.field
    async def pay_booking(self, info: Info, input: PayBookingInput) -> Booking:
        booking = await bff(info).pay_booking(
            await actor(info, ActorRole.STUDENT), input.booking_id, input.payment_method
        )
        return map_booking(booking)

    @strawberry.field
    async def cancel_booking(self, info: Info, input: CancelBookingInput) -> Booking:
        booking = await bff(info).cancel_booking(
            await actor(info, ActorRole.STUDENT, ActorRole.TEACHER),
            input.booking_id,
            input.reason,
        )
        return map_booking(booking)

    @strawberry.field
    async def complete_lesson(self, info: Info, input: CompleteLessonInput) -> Lesson:
        lesson = await bff(info).mark_lesson_completed(
            await actor(info, ActorRole.TEACHER), input.lesson_id
        )
        return map_lesson(lesson)

    @strawberry.field
    async def leave_review(self, info: Info, input: LeaveReviewInput) -> Review:
        review = await bff(info).add_review(
            await actor(info, ActorRole.STUDENT), input.lesson_id, input.rating, input.comment
        )
        return map_review(review)
