from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CHAR, CheckConstraint, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="chk_payments_amount"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(Uuid)
    student_id: Mapped[UUID] = mapped_column(Uuid)
    teacher_id: Mapped[UUID] = mapped_column(Uuid)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    payment_method: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(32), server_default=text("'CREATED'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    paid_at: Mapped[datetime | None]
    refunded_at: Mapped[datetime | None]
    failure_reason: Mapped[str | None] = mapped_column(Text)
    refund_reason: Mapped[str | None] = mapped_column(Text)
