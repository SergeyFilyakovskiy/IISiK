from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Lesson, ScheduleSlot


class SchedulingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        return await self.session.get(Lesson, lesson_id)

    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlot]:
        statement = (
            select(ScheduleSlot)
            .where(ScheduleSlot.teacher_id == teacher_id)
            .order_by(ScheduleSlot.weekday, ScheduleSlot.start_time, ScheduleSlot.id)
        )
        result = await self.session.scalars(statement)
        return list(result)

    async def list_available_lessons(
        self,
        teacher_id: UUID | None = None,
        subject_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
    ) -> list[Lesson]:
        conditions = [Lesson.status == "AVAILABLE"]
        if teacher_id is not None:
            conditions.append(Lesson.teacher_id == teacher_id)
        if subject_id is not None:
            conditions.append(Lesson.subject_id == subject_id)
        if start_from is not None:
            conditions.append(Lesson.start_at >= start_from)
        if end_to is not None:
            conditions.append(Lesson.start_at <= end_to)

        statement = select(Lesson).where(*conditions).order_by(Lesson.start_at, Lesson.id)
        result = await self.session.scalars(statement)
        return list(result)
