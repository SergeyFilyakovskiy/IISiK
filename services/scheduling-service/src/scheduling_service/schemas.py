from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from uuid import UUID


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
