from uuid import UUID

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .repositories import NotificationRepository
from .schemas import NotificationDTO


class NotificationService:
    def __init__(self, database: Database) -> None:
        self.repository = NotificationRepository(database)

    async def create_notification(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        source_event_id: UUID | None,
    ) -> NotificationDTO:
        return await self.repository.create_notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            body=body,
            source_event_id=source_event_id,
        )

    async def list_notifications(
        self,
        user_id: UUID,
        status: str | None = None,
        event_type: str | None = None,
        sort_direction: str = "DESC",
    ) -> list[NotificationDTO]:
        sort_direction = sort_direction.upper()
        if sort_direction not in {"ASC", "DESC"}:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "sort_direction must be ASC or DESC")
        return await self.repository.list_notifications(
            user_id=user_id,
            status=status,
            event_type=event_type,
            sort_direction=sort_direction,
        )
