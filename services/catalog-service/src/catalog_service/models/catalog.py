from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default=text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    teacher_links: Mapped[list[TeacherSubject]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Teacher(Base):
    __tablename__ = "teachers"
    __table_args__ = (
        CheckConstraint("experience_years >= 0", name="chk_teacher_experience"),
        CheckConstraint("price_per_lesson >= 0", name="chk_teacher_price"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    about: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int] = mapped_column(server_default=text("0"))
    price_per_lesson: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'BYN'"))
    profile_status: Mapped[str] = mapped_column(String(32), server_default=text("'ACTIVE'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    subject_links: Mapped[list[TeacherSubject]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )
    rating: Mapped[TeacherRatingCache | None] = relationship(
        back_populates="teacher", cascade="all, delete-orphan", uselist=False
    )


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"

    teacher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency_level: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    teacher: Mapped[Teacher] = relationship(back_populates="subject_links")
    subject: Mapped[Subject] = relationship(back_populates="teacher_links")


class TeacherRatingCache(Base):
    __tablename__ = "teacher_rating_cache"

    teacher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True
    )
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default=text("0"))
    reviews_count: Mapped[int] = mapped_column(server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    teacher: Mapped[Teacher] = relationship(back_populates="rating")
