from uuid import UUID

from shared.auth import CurrentUser, Role, require_role, require_student_owner
from shared.errors import DomainError, ErrorCode

from .clients import BookingClient
from .schemas import ReviewDTO
from .service import ReviewService


class ReviewWorkflowService:
    def __init__(self, service: ReviewService, booking: BookingClient) -> None:
        self.service = service
        self.booking = booking

    async def create_review(
        self,
        actor: CurrentUser,
        lesson_id: UUID,
        rating: int,
        comment: str | None,
    ) -> tuple[ReviewDTO, float, int]:
        require_role(actor, Role.STUDENT)
        if actor.student_id is None:
            raise DomainError(ErrorCode.FORBIDDEN, "Student profile is required")
        booking = await self.booking.get_by_lesson(str(lesson_id), actor)
        if booking is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Completed booking not found")
        require_student_owner(actor, UUID(booking.student_id))
        if booking.status != "COMPLETED":
            raise DomainError(ErrorCode.CONFLICT, "Review requires a completed booking")
        review = await self.service.create_review(
            lesson_id, actor.student_id, UUID(booking.teacher_id), rating, comment
        )
        average, count = await self.service.get_rating_stats(UUID(booking.teacher_id))
        return review, float(average), count
