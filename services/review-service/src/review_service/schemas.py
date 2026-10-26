from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReviewDTO:
    id: UUID
    lesson_id: UUID
    student_id: UUID
    teacher_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PageDTO[T]:
    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int
