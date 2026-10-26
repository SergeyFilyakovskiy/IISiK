from datetime import datetime
from uuid import UUID

from shared.database import Database

from .models import Lesson, ScheduleSlot
from .repositories import SchedulingRepository
from .schemas import LessonDTO, ScheduleSlotDTO


class SchedulingService:
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

    async def list_available_lessons(
        self,
        teacher_id: UUID | None = None,
        subject_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
    ) -> list[LessonDTO]:
        async with self.database.session() as session:
            lessons = await SchedulingRepository(session).list_available_lessons(
                teacher_id=teacher_id,
                subject_id=subject_id,
                start_from=start_from,
                end_to=end_to,
            )
            return [self._to_lesson_dto(lesson) for lesson in lessons]

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
