from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Lesson, ScheduleSlot


class SchedulingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        return await self.session.get(Lesson, lesson_id)

    async def get_schedule_slot(self, slot_id: UUID) -> ScheduleSlot | None:
        return await self.session.get(ScheduleSlot, slot_id)

    async def list_schedule(self, teacher_id: UUID) -> list[ScheduleSlot]:
        statement = (
            select(ScheduleSlot)
            .where(ScheduleSlot.teacher_id == teacher_id)
            .order_by(ScheduleSlot.weekday, ScheduleSlot.start_time, ScheduleSlot.id)
        )
        result = await self.session.scalars(statement)
        return list(result)

    async def list_overlapping_slots(
        self,
        teacher_id: UUID,
        weekday: int,
        start_time: time,
        end_time: time,
        exclude_slot_id: UUID | None = None,
    ) -> list[ScheduleSlot]:
        conditions = [
            ScheduleSlot.teacher_id == teacher_id,
            ScheduleSlot.weekday == weekday,
            ScheduleSlot.is_active,
            ScheduleSlot.start_time < end_time,
            ScheduleSlot.end_time > start_time,
        ]
        if exclude_slot_id is not None:
            conditions.append(ScheduleSlot.id != exclude_slot_id)
        result = await self.session.scalars(select(ScheduleSlot).where(*conditions))
        return list(result)

    async def list_potentially_overlapping_lessons(
        self,
        teacher_id: UUID,
        start_at: datetime,
        end_at: datetime,
        exclude_lesson_id: UUID | None = None,
    ) -> list[Lesson]:
        conditions = [
            Lesson.teacher_id == teacher_id,
            Lesson.status != "CANCELLED",
            Lesson.start_at < end_at,
        ]
        if exclude_lesson_id is not None:
            conditions.append(Lesson.id != exclude_lesson_id)
        result = await self.session.scalars(select(Lesson).where(*conditions))
        return list(result)

    async def update_lesson_status(
        self,
        lesson_id: UUID,
        allowed_statuses: tuple[str, ...],
        new_status: str,
        start_at: datetime | None = None,
    ) -> Lesson | None:
        values = {"status": new_status, "updated_at": func.now()}
        if start_at is not None:
            values["start_at"] = start_at
        statement = (
            update(Lesson)
            .where(Lesson.id == lesson_id, Lesson.status.in_(allowed_statuses))
            .values(**values)
            .returning(Lesson)
        )
        return await self.session.scalar(statement)

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
    ) -> list[Lesson]:
        conditions = [Lesson.status == (status or "AVAILABLE")]
        if teacher_id is not None:
            conditions.append(Lesson.teacher_id == teacher_id)
        if subject_id is not None:
            conditions.append(Lesson.subject_id == subject_id)
        if start_from is not None:
            conditions.append(Lesson.start_at >= start_from)
        if end_to is not None:
            conditions.append(Lesson.start_at <= end_to)
        if min_price is not None:
            conditions.append(Lesson.price >= min_price)
        if max_price is not None:
            conditions.append(Lesson.price <= max_price)

        sort_column = {
            "START_AT": Lesson.start_at,
            "PRICE": Lesson.price,
            "DURATION_MINUTES": Lesson.duration_minutes,
            "CREATED_AT": Lesson.created_at,
        }[sort_by]
        sort_order = sort_column.asc() if sort_direction == "ASC" else sort_column.desc()
        statement = select(Lesson).where(*conditions).order_by(sort_order, Lesson.id)
        result = await self.session.scalars(statement)
        return list(result)
