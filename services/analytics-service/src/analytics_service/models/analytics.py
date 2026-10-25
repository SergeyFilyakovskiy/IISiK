from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TeacherPeriodMetric(Base):
    __tablename__ = "teacher_period_metrics"

    teacher_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    period_date: Mapped[date] = mapped_column(primary_key=True)
    lessons_completed: Mapped[int] = mapped_column(server_default=text("0"))
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default=text("0"))
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default=text("0"))
    reviews_count: Mapped[int] = mapped_column(server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PlatformPeriodMetric(Base):
    __tablename__ = "platform_period_metrics"

    period_date: Mapped[date] = mapped_column(primary_key=True)
    lessons_completed: Mapped[int] = mapped_column(server_default=text("0"))
    bookings_created: Mapped[int] = mapped_column(server_default=text("0"))
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default=text("0"))
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default=text("0"))
    active_students: Mapped[int] = mapped_column(server_default=text("0"))
    active_teachers: Mapped[int] = mapped_column(server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
