from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .models import Review
from .schemas import ReviewDTO


class ReviewRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_review(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        rating: int,
        comment: str | None,
    ) -> ReviewDTO:
        async with self.database.session() as session:
            try:
                async with session.begin():
                    review = Review(
                        lesson_id=lesson_id,
                        student_id=student_id,
                        teacher_id=teacher_id,
                        rating=rating,
                        comment=comment,
                    )
                    session.add(review)
                    await session.flush()
            except IntegrityError as error:
                raise DomainError(
                    ErrorCode.CONFLICT, "Review for this lesson and student already exists"
                ) from error
            return self._to_dto(review)

    async def list_teacher_reviews(
        self,
        teacher_id: UUID,
        page: int,
        page_size: int,
        min_rating: int | None = None,
        sort_by: str = "CREATED_AT",
        sort_direction: str = "DESC",
    ) -> tuple[list[ReviewDTO], int]:
        filters = [Review.teacher_id == teacher_id]
        if min_rating is not None:
            filters.append(Review.rating >= min_rating)

        sort_columns = {
            "CREATED_AT": Review.created_at,
            "RATING": Review.rating,
            "UPDATED_AT": Review.updated_at,
        }
        sort_column = sort_columns.get(sort_by.upper())
        if sort_column is None:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported review sort field")
        direction = sort_direction.upper()
        if direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Unsupported sort direction")
        order_by = sort_column.asc() if direction == "ASC" else sort_column.desc()

        statement = (
            select(Review)
            .where(*filters)
            .order_by(order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_statement = select(func.count()).select_from(Review).where(*filters)

        async with self.database.session() as session:
            reviews = await session.scalars(statement)
            total_items = await session.scalar(count_statement)
            return [self._to_dto(review) for review in reviews], total_items or 0

    @staticmethod
    def _to_dto(review: Review) -> ReviewDTO:
        return ReviewDTO(
            id=review.id,
            lesson_id=review.lesson_id,
            student_id=review.student_id,
            teacher_id=review.teacher_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
