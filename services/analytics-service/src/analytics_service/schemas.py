from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TeacherMetricDTO:
    teacher_id: UUID
    period_date: date
    lessons_completed: int
    revenue: Decimal
    avg_rating: Decimal
    reviews_count: int


@dataclass(frozen=True, slots=True)
class AnalyticsReportDTO:
    period_from: date
    period_to: date
    lessons_completed: int
    bookings_created: int
    revenue: Decimal
    avg_rating: Decimal
    teachers: list[TeacherMetricDTO]
