from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CHAR, CheckConstraint, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("price >= 0", name="chk_bookings_price"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    lesson_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    student_id: Mapped[UUID] = mapped_column(Uuid)
    teacher_id: Mapped[UUID] = mapped_column(Uuid)
    subject_id: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(32), server_default=text("'PENDING_PAYMENT'"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'BYN'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    paid_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    cancel_reason: Mapped[str | None] = mapped_column(Text)
