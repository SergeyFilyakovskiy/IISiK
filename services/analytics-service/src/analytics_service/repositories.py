from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from shared.database import Database

from .models import PlatformPeriodMetric, TeacherPeriodMetric
from .schemas import TeacherMetricDTO


class AnalyticsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def list_teacher_metrics(
        self, period_from: date, period_to: date
    ) -> list[TeacherMetricDTO]:
        statement = (
            select(TeacherPeriodMetric)
            .where(TeacherPeriodMetric.period_date.between(period_from, period_to))
            .order_by(TeacherPeriodMetric.teacher_id, TeacherPeriodMetric.period_date)
        )
        async with self.database.session() as session:
            metrics = await session.scalars(statement)
            return [self._to_teacher_dto(metric) for metric in metrics]

    async def get_platform_totals(
        self, period_from: date, period_to: date
    ) -> tuple[int, int, Decimal]:
        statement = select(
            func.coalesce(func.sum(PlatformPeriodMetric.lessons_completed), 0),
            func.coalesce(func.sum(PlatformPeriodMetric.bookings_created), 0),
            func.coalesce(func.sum(PlatformPeriodMetric.revenue), 0),
        ).where(PlatformPeriodMetric.period_date.between(period_from, period_to))
        async with self.database.session() as session:
            lessons_completed, bookings_created, revenue = (await session.execute(statement)).one()
            return int(lessons_completed), int(bookings_created), Decimal(revenue)

    @staticmethod
    def _to_teacher_dto(metric: TeacherPeriodMetric) -> TeacherMetricDTO:
        return TeacherMetricDTO(
            teacher_id=metric.teacher_id,
            period_date=metric.period_date,
            lessons_completed=metric.lessons_completed,
            revenue=metric.revenue,
            avg_rating=metric.avg_rating,
            reviews_count=metric.reviews_count,
        )
