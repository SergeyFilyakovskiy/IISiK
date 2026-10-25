from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("lesson_id", "student_id", name="uq_reviews_lesson_student"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_reviews_rating"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    lesson_id: Mapped[UUID] = mapped_column(Uuid)
    student_id: Mapped[UUID] = mapped_column(Uuid)
    teacher_id: Mapped[UUID] = mapped_column(Uuid)
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
