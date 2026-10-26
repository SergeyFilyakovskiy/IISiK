from uuid import UUID

from sqlalchemy import select

from shared.database import Database

from .models import Notification
from .schemas import NotificationDTO


class NotificationRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def list_notifications(self, user_id: UUID) -> list[NotificationDTO]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        async with self.database.session() as session:
            notifications = await session.scalars(statement)
            return [self._to_dto(notification) for notification in notifications]

    @staticmethod
    def _to_dto(notification: Notification) -> NotificationDTO:
        return NotificationDTO(
            id=notification.id,
            user_id=notification.user_id,
            event_type=notification.event_type,
            title=notification.title,
            body=notification.body,
            status=notification.status,
            source_event_id=notification.source_event_id,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
        )
