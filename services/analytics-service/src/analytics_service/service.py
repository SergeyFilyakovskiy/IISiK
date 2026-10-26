from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from shared.database import Database

from .repositories import AnalyticsRepository
from .schemas import AnalyticsReportDTO, TeacherMetricDTO


@dataclass(slots=True)
class _TeacherTotals:
    teacher_id: UUID
    period_date: date
    lessons_completed: int = 0
    revenue: Decimal = Decimal("0")
    weighted_rating: Decimal = Decimal("0")
    reviews_count: int = 0


class AnalyticsService:
    def __init__(self, database: Database) -> None:
        self.repository = AnalyticsRepository(database)

    async def get_report(self, period_from: date, period_to: date) -> AnalyticsReportDTO:
        if period_from > period_to:
            raise ValueError("period_from must be earlier than or equal to period_to")

        metrics = await self.repository.list_teacher_metrics(period_from, period_to)
        lessons_completed, bookings_created, revenue = await self.repository.get_platform_totals(
            period_from, period_to
        )

        totals: dict[UUID, _TeacherTotals] = {}
        for metric in metrics:
            teacher = totals.setdefault(
                metric.teacher_id,
                _TeacherTotals(metric.teacher_id, metric.period_date),
            )
            teacher.period_date = max(teacher.period_date, metric.period_date)
            teacher.lessons_completed += metric.lessons_completed
            teacher.revenue += metric.revenue
            teacher.weighted_rating += metric.avg_rating * metric.reviews_count
            teacher.reviews_count += metric.reviews_count

        teachers = [
            TeacherMetricDTO(
                teacher_id=teacher.teacher_id,
                period_date=teacher.period_date,
                lessons_completed=teacher.lessons_completed,
                revenue=teacher.revenue,
                avg_rating=self._average(teacher.weighted_rating, teacher.reviews_count),
                reviews_count=teacher.reviews_count,
            )
            for teacher in totals.values()
        ]
        weighted_rating = sum(
            (teacher.weighted_rating for teacher in totals.values()), Decimal("0")
        )
        reviews_count = sum(teacher.reviews_count for teacher in totals.values())

        return AnalyticsReportDTO(
            period_from=period_from,
            period_to=period_to,
            lessons_completed=lessons_completed,
            bookings_created=bookings_created,
            revenue=revenue,
            avg_rating=self._average(weighted_rating, reviews_count),
            teachers=teachers,
        )

    @staticmethod
    def _average(weighted_rating: Decimal, reviews_count: int) -> Decimal:
        if reviews_count == 0:
            return Decimal("0")
        return weighted_rating / reviews_count
