from uuid import UUID

from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from .models import Subject, Teacher, TeacherRatingCache, TeacherSubject
from .schemas import TeacherFilterDTO


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_teacher(self, teacher_id: UUID) -> Teacher | None:
        statement = (
            select(Teacher).where(Teacher.id == teacher_id).options(*self._teacher_load_options())
        )
        return await self.session.scalar(statement)

    async def get_subject(self, subject_id: UUID) -> Subject | None:
        return await self.session.get(Subject, subject_id)

    async def list_subjects(self) -> list[Subject]:
        result = await self.session.scalars(select(Subject).order_by(Subject.name, Subject.id))
        return list(result)

    async def list_teachers(
        self,
        filters: TeacherFilterDTO,
        page: int,
        page_size: int,
    ) -> tuple[list[Teacher], int]:
        conditions = [Teacher.profile_status == "ACTIVE"]
        if filters.subject_id is not None:
            conditions.append(
                Teacher.subject_links.any(TeacherSubject.subject_id == filters.subject_id)
            )
        if filters.min_rating is not None:
            conditions.append(
                Teacher.rating.has(TeacherRatingCache.avg_rating >= filters.min_rating)
            )
        if filters.max_price is not None:
            conditions.append(Teacher.price_per_lesson <= filters.max_price)

        total_items = await self.session.scalar(
            select(func.count()).select_from(Teacher).where(*conditions)
        )
        sort_column = {
            "RATING": TeacherRatingCache.avg_rating,
            "PRICE": Teacher.price_per_lesson,
            "POPULARITY": TeacherRatingCache.reviews_count,
        }[filters.sort_by]
        sort_order = sort_column.asc() if filters.sort_direction == "ASC" else sort_column.desc()
        statement = (
            select(Teacher)
            .outerjoin(TeacherRatingCache)
            .where(*conditions)
            .options(*self._teacher_load_options())
            .order_by(nulls_last(sort_order), Teacher.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result), total_items or 0

    @staticmethod
    def _teacher_load_options() -> tuple[ExecutableOption, ...]:
        return (
            selectinload(Teacher.subject_links).selectinload(TeacherSubject.subject),
            selectinload(Teacher.rating),
        )
