from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class SubjectDTO:
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TeacherSubjectDTO:
    subject: SubjectDTO
    proficiency_level: str | None


@dataclass(slots=True)
class RatingDTO:
    teacher_id: UUID
    avg_rating: Decimal
    reviews_count: int
    updated_at: datetime


@dataclass(slots=True)
class TeacherDTO:
    id: UUID
    user_id: UUID
    about: str | None
    experience_years: int
    price_per_lesson: Decimal
    currency: str
    profile_status: str
    created_at: datetime
    updated_at: datetime
    subjects: list[TeacherSubjectDTO]
    rating: RatingDTO | None


@dataclass(slots=True)
class TeacherFilterDTO:
    subject_id: UUID | None = None
    min_rating: Decimal | None = None
    max_price: Decimal | None = None
    sort_by: str = "RATING"
    sort_direction: str = "DESC"


@dataclass(slots=True)
class PageDTO[ItemT]:
    items: list[ItemT]
    page: int
    page_size: int
    total_items: int
    total_pages: int
