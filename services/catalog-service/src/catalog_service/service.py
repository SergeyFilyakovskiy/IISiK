from dataclasses import replace
from math import ceil
from uuid import UUID

from shared.database import Database

from .models import Subject, Teacher, TeacherRatingCache, TeacherSubject
from .repositories import CatalogRepository
from .schemas import (
    PageDTO,
    RatingDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
    TeacherSubjectDTO,
)


class CatalogService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_teacher(self, teacher_id: UUID) -> TeacherDTO | None:
        async with self.database.session() as session:
            teacher = await CatalogRepository(session).get_teacher(teacher_id)
            return self._to_teacher_dto(teacher) if teacher is not None else None

    async def get_subject(self, subject_id: UUID) -> SubjectDTO | None:
        async with self.database.session() as session:
            subject = await CatalogRepository(session).get_subject(subject_id)
            return self._to_subject_dto(subject) if subject is not None else None

    async def list_subjects(self) -> list[SubjectDTO]:
        async with self.database.session() as session:
            subjects = await CatalogRepository(session).list_subjects()
            return [self._to_subject_dto(subject) for subject in subjects]

    async def list_teachers(
        self,
        filters: TeacherFilterDTO,
        page: int = 1,
        page_size: int = 20,
    ) -> PageDTO[TeacherDTO]:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        sort_by = filters.sort_by.upper()
        sort_direction = filters.sort_direction.upper()
        if sort_by not in {"RATING", "PRICE", "POPULARITY"}:
            raise ValueError("sort_by must be RATING, PRICE, or POPULARITY")
        if sort_direction not in {"ASC", "DESC"}:
            raise ValueError("sort_direction must be ASC or DESC")
        normalized_filters = replace(filters, sort_by=sort_by, sort_direction=sort_direction)

        async with self.database.session() as session:
            teachers, total_items = await CatalogRepository(session).list_teachers(
                normalized_filters, page, page_size
            )
        return PageDTO(
            items=[self._to_teacher_dto(teacher) for teacher in teachers],
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=ceil(total_items / page_size),
        )

    @classmethod
    def _to_teacher_dto(cls, teacher: Teacher) -> TeacherDTO:
        return TeacherDTO(
            id=teacher.id,
            user_id=teacher.user_id,
            about=teacher.about,
            experience_years=teacher.experience_years,
            price_per_lesson=teacher.price_per_lesson,
            currency=teacher.currency,
            profile_status=teacher.profile_status,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
            subjects=[cls._to_teacher_subject_dto(link) for link in teacher.subject_links],
            rating=cls._to_rating_dto(teacher.rating) if teacher.rating is not None else None,
        )

    @classmethod
    def _to_teacher_subject_dto(cls, link: TeacherSubject) -> TeacherSubjectDTO:
        return TeacherSubjectDTO(
            subject=cls._to_subject_dto(link.subject),
            proficiency_level=link.proficiency_level,
        )

    @staticmethod
    def _to_subject_dto(subject: Subject) -> SubjectDTO:
        return SubjectDTO(
            id=subject.id,
            name=subject.name,
            description=subject.description,
            is_active=subject.is_active,
            created_at=subject.created_at,
            updated_at=subject.updated_at,
        )

    @staticmethod
    def _to_rating_dto(rating: TeacherRatingCache) -> RatingDTO:
        return RatingDTO(
            teacher_id=rating.teacher_id,
            avg_rating=rating.avg_rating,
            reviews_count=rating.reviews_count,
            updated_at=rating.updated_at,
        )
