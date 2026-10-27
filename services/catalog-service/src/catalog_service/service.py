from dataclasses import replace
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from shared.database import Database
from shared.errors import DomainError, ErrorCode

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

    async def create_teacher_profile(
        self,
        user_id: UUID,
        about: str | None,
        experience_years: int,
        price_per_lesson: Decimal,
        currency: str,
        subject_ids: list[UUID],
    ) -> TeacherDTO:
        self._validate_experience(experience_years)
        self._validate_price(price_per_lesson)
        normalized_currency = self._validate_currency(currency)
        unique_subject_ids = list(dict.fromkeys(subject_ids))

        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                if await repository.get_teacher_by_user_id(user_id) is not None:
                    raise DomainError(
                        ErrorCode.CONFLICT, "Teacher profile already exists for this user"
                    )
                subjects = await self._get_active_subjects(repository, unique_subject_ids)
                teacher = Teacher(
                    user_id=user_id,
                    about=about,
                    experience_years=experience_years,
                    price_per_lesson=price_per_lesson,
                    currency=normalized_currency,
                )
                session.add(teacher)
                await session.flush()
                for subject in subjects:
                    session.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DomainError(
                    ErrorCode.CONFLICT, "Teacher profile already exists for this user"
                ) from exc
            except Exception:
                await session.rollback()
                raise

            teacher = await self._require_teacher(repository, teacher.id)
            return self._to_teacher_dto(teacher)

    async def update_teacher_profile(
        self,
        teacher_id: UUID,
        about: str | None = None,
        experience_years: int | None = None,
        price_per_lesson: Decimal | None = None,
        currency: str | None = None,
        profile_status: str | None = None,
    ) -> TeacherDTO:
        if experience_years is not None:
            self._validate_experience(experience_years)
        if price_per_lesson is not None:
            self._validate_price(price_per_lesson)
        normalized_currency = self._validate_currency(currency) if currency is not None else None

        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                teacher = await self._require_teacher(repository, teacher_id)
                if about is not None:
                    teacher.about = about
                if experience_years is not None:
                    teacher.experience_years = experience_years
                if price_per_lesson is not None:
                    teacher.price_per_lesson = price_per_lesson
                if normalized_currency is not None:
                    teacher.currency = normalized_currency
                if profile_status is not None:
                    teacher.profile_status = profile_status
                teacher.updated_at = func.now()
                await session.commit()
            except Exception:
                await session.rollback()
                raise

            teacher = await self._require_teacher(repository, teacher_id)
            return self._to_teacher_dto(teacher)

    async def add_teacher_subject(
        self,
        teacher_id: UUID,
        subject_id: UUID,
        proficiency_level: str | None,
    ) -> TeacherDTO:
        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                teacher = await self._require_teacher(repository, teacher_id)
                subject = await repository.get_subject(subject_id)
                if subject is None:
                    raise DomainError(ErrorCode.NOT_FOUND, "Subject not found")
                if not subject.is_active:
                    raise DomainError(
                        ErrorCode.VALIDATION_ERROR, "Only active subjects can be linked"
                    )
                link = next(
                    (link for link in teacher.subject_links if link.subject_id == subject_id),
                    None,
                )
                if link is None:
                    session.add(
                        TeacherSubject(
                            teacher_id=teacher_id,
                            subject_id=subject_id,
                            proficiency_level=proficiency_level,
                        )
                    )
                else:
                    link.proficiency_level = proficiency_level
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DomainError(ErrorCode.CONFLICT, "Teacher subject link conflict") from exc
            except Exception:
                await session.rollback()
                raise

            teacher = await self._require_teacher(repository, teacher_id)
            return self._to_teacher_dto(teacher)

    async def remove_teacher_subject(self, teacher_id: UUID, subject_id: UUID) -> TeacherDTO:
        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                teacher = await self._require_teacher(repository, teacher_id)
                link = next(
                    (link for link in teacher.subject_links if link.subject_id == subject_id),
                    None,
                )
                if link is None:
                    raise DomainError(ErrorCode.NOT_FOUND, "Teacher subject link not found")
                await session.delete(link)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

            teacher = await self._require_teacher(repository, teacher_id)
            return self._to_teacher_dto(teacher)

    async def create_subject(
        self, name: str, description: str | None, is_active: bool = True
    ) -> SubjectDTO:
        normalized_name = self._validate_subject_name(name)
        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                if await repository.get_subject_by_name(normalized_name) is not None:
                    raise DomainError(ErrorCode.CONFLICT, "Subject name already exists")
                subject = Subject(
                    name=normalized_name, description=description, is_active=is_active
                )
                session.add(subject)
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DomainError(ErrorCode.CONFLICT, "Subject name already exists") from exc
            except Exception:
                await session.rollback()
                raise

            return self._to_subject_dto(subject)

    async def update_subject(
        self,
        subject_id: UUID,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> SubjectDTO:
        normalized_name = self._validate_subject_name(name) if name is not None else None
        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                subject = await repository.get_subject(subject_id)
                if subject is None:
                    raise DomainError(ErrorCode.NOT_FOUND, "Subject not found")
                if normalized_name is not None:
                    existing = await repository.get_subject_by_name(
                        normalized_name, exclude_subject_id=subject_id
                    )
                    if existing is not None:
                        raise DomainError(ErrorCode.CONFLICT, "Subject name already exists")
                    subject.name = normalized_name
                if description is not None:
                    subject.description = description
                if is_active is not None:
                    subject.is_active = is_active
                subject.updated_at = func.now()
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DomainError(ErrorCode.CONFLICT, "Subject name already exists") from exc
            except Exception:
                await session.rollback()
                raise

            return self._to_subject_dto(subject)

    async def recalculate_rating(
        self, teacher_id: UUID, avg_rating: Decimal, reviews_count: int
    ) -> RatingDTO:
        if not avg_rating.is_finite() or not 0 <= avg_rating <= 5:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "avg_rating must be between 0 and 5")
        if reviews_count < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "reviews_count must be greater than or equal to 0"
            )

        async with self.database.session() as session:
            repository = CatalogRepository(session)
            try:
                teacher = await self._require_teacher(repository, teacher_id)
                rating = teacher.rating
                if rating is None:
                    rating = TeacherRatingCache(
                        teacher_id=teacher_id,
                        avg_rating=avg_rating,
                        reviews_count=reviews_count,
                    )
                    session.add(rating)
                else:
                    rating.avg_rating = avg_rating
                    rating.reviews_count = reviews_count
                rating.updated_at = func.now()
                await session.commit()
            except Exception:
                await session.rollback()
                raise

            return self._to_rating_dto(rating)

    async def list_subjects(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        sort_direction: str = "ASC",
    ) -> list[SubjectDTO]:
        normalized_direction = sort_direction.upper()
        if normalized_direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "sort_direction must be ASC or DESC")
        normalized_search = search.strip() if search is not None else None
        async with self.database.session() as session:
            subjects = await CatalogRepository(session).list_subjects(
                search=normalized_search,
                is_active=is_active,
                sort_direction=normalized_direction,
            )
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

    @staticmethod
    async def _require_teacher(repository: CatalogRepository, teacher_id: UUID) -> Teacher:
        teacher = await repository.get_teacher(teacher_id)
        if teacher is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Teacher not found")
        return teacher

    @staticmethod
    async def _get_active_subjects(
        repository: CatalogRepository, subject_ids: list[UUID]
    ) -> list[Subject]:
        subjects = await repository.list_subjects_by_ids(subject_ids)
        subjects_by_id = {subject.id: subject for subject in subjects}
        missing_ids = [subject_id for subject_id in subject_ids if subject_id not in subjects_by_id]
        if missing_ids:
            raise DomainError(ErrorCode.NOT_FOUND, "One or more subjects not found")
        if any(not subject.is_active for subject in subjects):
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "Only active subjects can be linked to a teacher"
            )
        return [subjects_by_id[subject_id] for subject_id in subject_ids]

    @staticmethod
    def _validate_experience(experience_years: int) -> None:
        if experience_years < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "experience_years must be greater than or equal to 0"
            )

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if not price.is_finite() or price < 0:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR, "price_per_lesson must be greater than or equal to 0"
            )

    @staticmethod
    def _validate_currency(currency: str) -> str:
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "currency must contain 3 characters")
        return normalized_currency

    @staticmethod
    def _validate_subject_name(name: str) -> str:
        normalized_name = name.strip()
        if not normalized_name:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Subject name must not be empty")
        return normalized_name

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
