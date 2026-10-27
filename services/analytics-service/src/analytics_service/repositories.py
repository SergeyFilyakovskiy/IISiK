from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import Database

from .models import AnalyticsProcessedEvent, PlatformPeriodMetric, TeacherPeriodMetric
from .schemas import TeacherMetricDTO


class AnalyticsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record_booking_created(self, event_id: UUID, period_date: date) -> None:
        async with self.database.session() as session:
            if not await self._process_event(session, event_id, "booking_created"):
                return
            statement = insert(PlatformPeriodMetric).values(
                period_date=period_date,
                bookings_created=1,
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=["period_date"],
                    set_={
                        "bookings_created": PlatformPeriodMetric.bookings_created
                        + statement.excluded.bookings_created,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.commit()

    async def record_payment(
        self,
        event_id: UUID,
        teacher_id: UUID,
        period_date: date,
        amount: Decimal,
    ) -> None:
        async with self.database.session() as session:
            if not await self._process_event(session, event_id, "payment"):
                return
            teacher_statement = insert(TeacherPeriodMetric).values(
                teacher_id=teacher_id,
                period_date=period_date,
                revenue=amount,
            )
            await session.execute(
                teacher_statement.on_conflict_do_update(
                    index_elements=["teacher_id", "period_date"],
                    set_={
                        "revenue": TeacherPeriodMetric.revenue + teacher_statement.excluded.revenue,
                        "updated_at": func.now(),
                    },
                )
            )
            platform_statement = insert(PlatformPeriodMetric).values(
                period_date=period_date,
                revenue=amount,
            )
            await session.execute(
                platform_statement.on_conflict_do_update(
                    index_elements=["period_date"],
                    set_={
                        "revenue": PlatformPeriodMetric.revenue
                        + platform_statement.excluded.revenue,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.commit()

    async def record_lesson_completed(
        self, event_id: UUID, teacher_id: UUID, period_date: date
    ) -> None:
        async with self.database.session() as session:
            if not await self._process_event(session, event_id, "lesson_completed"):
                return
            teacher_statement = insert(TeacherPeriodMetric).values(
                teacher_id=teacher_id,
                period_date=period_date,
                lessons_completed=1,
            )
            await session.execute(
                teacher_statement.on_conflict_do_update(
                    index_elements=["teacher_id", "period_date"],
                    set_={
                        "lessons_completed": TeacherPeriodMetric.lessons_completed
                        + teacher_statement.excluded.lessons_completed,
                        "updated_at": func.now(),
                    },
                )
            )
            platform_statement = insert(PlatformPeriodMetric).values(
                period_date=period_date,
                lessons_completed=1,
            )
            await session.execute(
                platform_statement.on_conflict_do_update(
                    index_elements=["period_date"],
                    set_={
                        "lessons_completed": PlatformPeriodMetric.lessons_completed
                        + platform_statement.excluded.lessons_completed,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.commit()

    async def record_review(
        self,
        event_id: UUID,
        teacher_id: UUID,
        period_date: date,
        rating: int,
    ) -> None:
        async with self.database.session() as session:
            if not await self._process_event(session, event_id, "review"):
                return
            teacher_statement = insert(TeacherPeriodMetric).values(
                teacher_id=teacher_id,
                period_date=period_date,
                avg_rating=rating,
                reviews_count=1,
            )
            await session.execute(
                teacher_statement.on_conflict_do_update(
                    index_elements=["teacher_id", "period_date"],
                    set_={
                        "avg_rating": (
                            TeacherPeriodMetric.avg_rating * TeacherPeriodMetric.reviews_count
                            + teacher_statement.excluded.avg_rating
                        )
                        / (TeacherPeriodMetric.reviews_count + 1),
                        "reviews_count": TeacherPeriodMetric.reviews_count + 1,
                        "updated_at": func.now(),
                    },
                )
            )
            platform_statement = insert(PlatformPeriodMetric).values(
                period_date=period_date,
                avg_rating=rating,
                reviews_count=1,
            )
            await session.execute(
                platform_statement.on_conflict_do_update(
                    index_elements=["period_date"],
                    set_={
                        "avg_rating": (
                            PlatformPeriodMetric.avg_rating * PlatformPeriodMetric.reviews_count
                            + platform_statement.excluded.avg_rating
                        )
                        / (PlatformPeriodMetric.reviews_count + 1),
                        "reviews_count": PlatformPeriodMetric.reviews_count + 1,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.commit()

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
    ) -> tuple[int, int, Decimal, Decimal, int]:
        statement = select(
            func.coalesce(func.sum(PlatformPeriodMetric.lessons_completed), 0),
            func.coalesce(func.sum(PlatformPeriodMetric.bookings_created), 0),
            func.coalesce(func.sum(PlatformPeriodMetric.revenue), 0),
            func.coalesce(
                func.sum(PlatformPeriodMetric.avg_rating * PlatformPeriodMetric.reviews_count),
                0,
            ),
            func.coalesce(func.sum(PlatformPeriodMetric.reviews_count), 0),
        ).where(PlatformPeriodMetric.period_date.between(period_from, period_to))
        async with self.database.session() as session:
            totals = (await session.execute(statement)).one()
            return (
                int(totals[0]),
                int(totals[1]),
                Decimal(totals[2]),
                Decimal(totals[3]),
                int(totals[4]),
            )

    @staticmethod
    async def _process_event(session: AsyncSession, event_id: UUID, event_type: str) -> bool:
        statement = (
            insert(AnalyticsProcessedEvent)
            .values(event_id=event_id, event_type=event_type)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(AnalyticsProcessedEvent.event_id)
        )
        return await session.scalar(statement) is not None

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
