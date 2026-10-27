from uuid import UUID

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .repositories import ReviewRepository
from .schemas import PageDTO, ReviewDTO


class ReviewService:
    def __init__(self, database: Database) -> None:
        self.repository = ReviewRepository(database)

    async def create_review(
        self,
        lesson_id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        rating: int,
        comment: str | None,
    ) -> ReviewDTO:
        if not 1 <= rating <= 5:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Review rating must be between 1 and 5")
        return await self.repository.create_review(
            lesson_id, student_id, teacher_id, rating, comment
        )

    async def list_teacher_reviews(
        self,
        teacher_id: UUID,
        page: int = 1,
        page_size: int = 20,
        min_rating: int | None = None,
        sort_by: str = "CREATED_AT",
        sort_direction: str = "DESC",
    ) -> PageDTO[ReviewDTO]:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        reviews, total_items = await self.repository.list_teacher_reviews(
            teacher_id, page, page_size, min_rating, sort_by, sort_direction
        )
        return PageDTO(
            items=reviews,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(total_items + page_size - 1) // page_size,
        )
