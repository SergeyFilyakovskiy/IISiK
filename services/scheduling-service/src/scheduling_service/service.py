from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .models import Lesson, ScheduleSlot
from .repositories import SchedulingRepository
from .schemas import LessonDTO, ScheduleSlotDTO


class SchedulingService:
    _LESSON_STATUSES = {"AVAILABLE", "RESERVED", "BOOKED", "COMPLETED", "CANCELLED"}

    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_lesson(self, lesson_id: UUID) -> LessonDTO | None:
        async with self.database.session() as session:
            lesson = await SchedulingRepository(session).get_lesson(lesson_id)
            return self._to_lesson_dto(lesson) if lesson is not None else None

    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlotDTO]:
        async with self.database.session() as session:
            slots = await SchedulingRepository(session).list_schedule(teacher_id)
            return [self._to_schedule_slot_dto(slot) for slot in slots]

    async def create_schedule_slot(
        self,
        teacher_id: UUID,
        weekday: int,
        start_time: time,
        end_time: time,
    ) -> ScheduleSlotDTO:
        self._validate_slot_times(weekday, start_time, end_time)
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            try:
                await self._ensure_no_slot_overlap(
                    repository, teacher_id, weekday, start_time, end_time
                )
                slot = ScheduleSlot(
                    teacher_id=teacher_id,
                    weekday=weekday,
                    start_time=start_time,
                    end_time=end_time,
                )
                session.add(slot)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return self._to_schedule_slot_dto(slot)

    async def update_schedule_slot(
        self,
        slot_id: UUID,
        weekday: int | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        is_active: bool | None = None,
    ) -> ScheduleSlotDTO:
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            try:
                slot = await self._require_slot(repository, slot_id)
                new_weekday = weekday if weekday is not None else slot.weekday
                new_start_time = start_time if start_time is not None else slot.start_time
                new_end_time = end_time if end_time is not None else slot.end_time
                new_is_active = is_active if is_active is not None else slot.is_active
                self._validate_slot_times(new_weekday, new_start_time, new_end_time)
                if new_is_active:
                    await self._ensure_no_slot_overlap(
                        repository,
                        slot.teacher_id,
                        new_weekday,
                        new_start_time,
                        new_end_time,
                        exclude_slot_id=slot_id,
                    )
                slot.weekday = new_weekday
                slot.start_time = new_start_time
                slot.end_time = new_end_time
                slot.is_active = new_is_active
                slot.updated_at = func.now()
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return self._to_schedule_slot_dto(slot)

    async def delete_schedule_slot(self, slot_id: UUID) -> bool:
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            slot = await repository.get_schedule_slot(slot_id)
            if slot is None:
                return False
            try:
                await session.delete(slot)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return True

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
        self._validate_lesson(start_at, duration_minutes, price)
        normalized_currency = self._validate_currency(currency)
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            try:
                if schedule_slot_id is not None:
                    slot = await self._require_slot(repository, schedule_slot_id)
                    self._validate_lesson_slot(
                        slot, teacher_id, start_at, duration_minutes, require_active=True
                    )
                await self._ensure_no_lesson_overlap(
                    repository, teacher_id, start_at, duration_minutes
                )
                lesson = Lesson(
                    teacher_id=teacher_id,
                    subject_id=subject_id,
                    schedule_slot_id=schedule_slot_id,
                    start_at=start_at,
                    duration_minutes=duration_minutes,
                    price=price,
                    currency=normalized_currency,
                )
                session.add(lesson)
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DomainError(
                    ErrorCode.CONFLICT, "Lesson conflicts with existing data"
                ) from exc
            except Exception:
                await session.rollback()
                raise
            return self._to_lesson_dto(lesson)

    async def cancel_lesson(self, lesson_id: UUID, reason: str | None = None) -> LessonDTO:
        return await self._transition_lesson(
            lesson_id, ("AVAILABLE", "RESERVED", "BOOKED"), "CANCELLED"
        )

    async def reschedule_lesson(self, lesson_id: UUID, new_start_at: datetime) -> LessonDTO:
        self._validate_future_start(new_start_at)
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            try:
                lesson = await self._require_lesson(repository, lesson_id)
                if lesson.status not in {"AVAILABLE", "RESERVED"}:
                    raise DomainError(
                        ErrorCode.CONFLICT, "Only available or reserved lessons can be rescheduled"
                    )
                if lesson.schedule_slot_id is not None:
                    slot = await self._require_slot(repository, lesson.schedule_slot_id)
                    self._validate_lesson_slot(
                        slot,
                        lesson.teacher_id,
                        new_start_at,
                        lesson.duration_minutes,
                        require_active=True,
                    )
                await self._ensure_no_lesson_overlap(
                    repository,
                    lesson.teacher_id,
                    new_start_at,
                    lesson.duration_minutes,
                    exclude_lesson_id=lesson_id,
                )
                updated = await repository.update_lesson_status(
                    lesson_id,
                    (lesson.status,),
                    lesson.status,
                    start_at=new_start_at,
                )
                if updated is None:
                    raise DomainError(ErrorCode.CONFLICT, "Lesson status changed concurrently")
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return self._to_lesson_dto(updated)

    async def reserve_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self._transition_lesson(lesson_id, ("AVAILABLE",), "RESERVED")

    async def release_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self._transition_lesson(lesson_id, ("RESERVED", "BOOKED"), "AVAILABLE")

    async def mark_lesson_booked(self, lesson_id: UUID) -> LessonDTO:
        return await self._transition_lesson(lesson_id, ("RESERVED",), "BOOKED")

    async def complete_lesson(self, lesson_id: UUID) -> LessonDTO:
        return await self._transition_lesson(lesson_id, ("BOOKED",), "COMPLETED")

    async def list_available_lessons(
        self,
        teacher_id: UUID | None = None,
        subject_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
        status: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort_by: str = "START_AT",
        sort_direction: str = "ASC",
    ) -> list[LessonDTO]:
        normalized_status = status.upper() if status is not None else None
        if normalized_status is not None and normalized_status not in self._LESSON_STATUSES:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unknown lesson status")
        normalized_sort_by = sort_by.upper()
        if normalized_sort_by not in {"START_AT", "PRICE", "DURATION_MINUTES", "CREATED_AT"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported lesson sort field")
        normalized_direction = sort_direction.upper()
        if normalized_direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "sort_direction must be ASC or DESC")
        self._validate_price_filters(min_price, max_price)
        if start_from is not None and end_to is not None and start_from > end_to:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "start_from must be less than or equal to end_to"
            )

        async with self.database.session() as session:
            lessons = await SchedulingRepository(session).list_available_lessons(
                teacher_id=teacher_id,
                subject_id=subject_id,
                start_from=start_from,
                end_to=end_to,
                status=normalized_status,
                min_price=min_price,
                max_price=max_price,
                sort_by=normalized_sort_by,
                sort_direction=normalized_direction,
            )
            return [self._to_lesson_dto(lesson) for lesson in lessons]

    async def _transition_lesson(
        self, lesson_id: UUID, allowed_statuses: tuple[str, ...], new_status: str
    ) -> LessonDTO:
        async with self.database.session() as session:
            repository = SchedulingRepository(session)
            try:
                lesson = await repository.update_lesson_status(
                    lesson_id, allowed_statuses, new_status
                )
                if lesson is None:
                    existing = await repository.get_lesson(lesson_id)
                    if existing is None:
                        raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
                    raise DomainError(
                        ErrorCode.CONFLICT,
                        f"Lesson cannot change from {existing.status} to {new_status}",
                    )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return self._to_lesson_dto(lesson)

    @staticmethod
    async def _require_slot(repository: SchedulingRepository, slot_id: UUID) -> ScheduleSlot:
        slot = await repository.get_schedule_slot(slot_id)
        if slot is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Schedule slot not found")
        return slot

    @staticmethod
    async def _require_lesson(repository: SchedulingRepository, lesson_id: UUID) -> Lesson:
        lesson = await repository.get_lesson(lesson_id)
        if lesson is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
        return lesson

    @staticmethod
    def _validate_slot_times(weekday: int, start_time: time, end_time: time) -> None:
        if not 1 <= weekday <= 7:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "weekday must be between 1 and 7")
        if start_time >= end_time:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "start_time must be before end_time")

    @staticmethod
    async def _ensure_no_slot_overlap(
        repository: SchedulingRepository,
        teacher_id: UUID,
        weekday: int,
        start_time: time,
        end_time: time,
        exclude_slot_id: UUID | None = None,
    ) -> None:
        overlaps = await repository.list_overlapping_slots(
            teacher_id, weekday, start_time, end_time, exclude_slot_id
        )
        if overlaps:
            raise DomainError(ErrorCode.CONFLICT, "Schedule slot overlaps an active slot")

    @staticmethod
    def _validate_lesson(start_at: datetime, duration_minutes: int, price: Decimal) -> None:
        if duration_minutes <= 0:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "duration_minutes must be greater than 0")
        if not price.is_finite() or price < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "price must be greater than or equal to 0"
            )
        SchedulingService._validate_future_start(start_at)

    @staticmethod
    def _validate_future_start(start_at: datetime) -> None:
        now = datetime.now(start_at.tzinfo) if start_at.tzinfo is not None else datetime.now()
        if start_at <= now:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Lesson start must be in the future")

    @staticmethod
    def _validate_currency(currency: str) -> str:
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "currency must contain 3 characters")
        return normalized_currency

    @staticmethod
    def _validate_lesson_slot(
        slot: ScheduleSlot,
        teacher_id: UUID,
        start_at: datetime,
        duration_minutes: int,
        require_active: bool,
    ) -> None:
        if require_active and not slot.is_active:
            raise DomainError(ErrorCode.CONFLICT, "Schedule slot is inactive")
        if slot.teacher_id != teacher_id:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Schedule slot belongs to another teacher"
            )
        end_at = start_at + timedelta(minutes=duration_minutes)
        if (
            slot.weekday != start_at.isoweekday()
            or start_at.time() < slot.start_time
            or end_at.date() != start_at.date()
            or end_at.time() > slot.end_time
        ):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Lesson does not fit the selected schedule slot"
            )

    @staticmethod
    async def _ensure_no_lesson_overlap(
        repository: SchedulingRepository,
        teacher_id: UUID,
        start_at: datetime,
        duration_minutes: int,
        exclude_lesson_id: UUID | None = None,
    ) -> None:
        end_at = start_at + timedelta(minutes=duration_minutes)
        candidates = await repository.list_potentially_overlapping_lessons(
            teacher_id, start_at, end_at, exclude_lesson_id
        )
        if any(
            candidate.start_at + timedelta(minutes=candidate.duration_minutes) > start_at
            for candidate in candidates
        ):
            raise DomainError(ErrorCode.CONFLICT, "Lesson overlaps another lesson")

    @staticmethod
    def _validate_price_filters(min_price: Decimal | None, max_price: Decimal | None) -> None:
        if min_price is not None and (not min_price.is_finite() or min_price < 0):
            raise DomainError(ErrorCode.VALIDATION_ERROR, "min_price must not be negative")
        if max_price is not None and (not max_price.is_finite() or max_price < 0):
            raise DomainError(ErrorCode.VALIDATION_ERROR, "max_price must not be negative")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "min_price must be less than or equal to max_price"
            )

    @staticmethod
    def _to_schedule_slot_dto(slot: ScheduleSlot) -> ScheduleSlotDTO:
        return ScheduleSlotDTO(
            id=slot.id,
            teacher_id=slot.teacher_id,
            weekday=slot.weekday,
            start_time=slot.start_time,
            end_time=slot.end_time,
            is_active=slot.is_active,
            created_at=slot.created_at,
            updated_at=slot.updated_at,
        )

    @staticmethod
    def _to_lesson_dto(lesson: Lesson) -> LessonDTO:
        return LessonDTO(
            id=lesson.id,
            teacher_id=lesson.teacher_id,
            subject_id=lesson.subject_id,
            schedule_slot_id=lesson.schedule_slot_id,
            start_at=lesson.start_at,
            duration_minutes=lesson.duration_minutes,
            status=lesson.status,
            price=lesson.price,
            currency=lesson.currency,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )
