from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Time,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="chk_schedule_weekday"),
        CheckConstraint("start_time < end_time", name="chk_schedule_time"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    teacher_id: Mapped[UUID] = mapped_column(Uuid)
    weekday: Mapped[int] = mapped_column(SmallInteger)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(server_default=text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    lessons: Mapped[list[Lesson]] = relationship(back_populates="schedule_slot")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="chk_lessons_duration"),
        CheckConstraint("price >= 0", name="chk_lessons_price"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    teacher_id: Mapped[UUID] = mapped_column(Uuid)
    subject_id: Mapped[UUID] = mapped_column(Uuid)
    schedule_slot_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("schedule_slots.id", ondelete="SET NULL")
    )
    start_at: Mapped[datetime]
    duration_minutes: Mapped[int] = mapped_column(server_default=text("60"))
    status: Mapped[str] = mapped_column(String(32), server_default=text("'AVAILABLE'"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'BYN'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    schedule_slot: Mapped[ScheduleSlot | None] = relationship(back_populates="lessons")
