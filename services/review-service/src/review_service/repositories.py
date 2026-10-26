from uuid import UUID

from sqlalchemy import func, select

from shared.database import Database

from .models import Review
from .schemas import ReviewDTO


class ReviewRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def list_teacher_reviews(
        self, teacher_id: UUID, page: int, page_size: int
    ) -> tuple[list[ReviewDTO], int]:
        filters = Review.teacher_id == teacher_id
        statement = (
            select(Review)
            .where(filters)
            .order_by(Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_statement = select(func.count()).select_from(Review).where(filters)

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
