from uuid import UUID

from shared.database import Database

from .repositories import NotificationRepository
from .schemas import NotificationDTO


class NotificationService:
    def __init__(self, database: Database) -> None:
        self.repository = NotificationRepository(database)

    async def list_notifications(self, user_id: UUID) -> list[NotificationDTO]:
        return await self.repository.list_notifications(user_id)
