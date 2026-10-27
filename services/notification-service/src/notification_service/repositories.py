from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError

from shared.database import Database

from .models import Notification
from .schemas import NotificationDTO


class NotificationRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_notification(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        source_event_id: UUID | None,
    ) -> NotificationDTO:
        async with self.database.session() as session:
            existing = await session.scalar(self._find_by_source(event_type, source_event_id))
            if existing is not None:
                return self._to_dto(existing)

            notification = Notification(
                user_id=user_id,
                event_type=event_type,
                title=title,
                body=body,
                source_event_id=source_event_id,
            )
            session.add(notification)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await session.scalar(self._find_by_source(event_type, source_event_id))
                if existing is None:
                    raise
                return self._to_dto(existing)
            await session.refresh(notification)
            return self._to_dto(notification)

    async def list_notifications(
        self,
        user_id: UUID,
        status: str | None = None,
        event_type: str | None = None,
        sort_direction: str = "DESC",
    ) -> list[NotificationDTO]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if status is not None:
            statement = statement.where(Notification.status == status)
        if event_type is not None:
            statement = statement.where(Notification.event_type == event_type)
        sort_order = (
            Notification.created_at.asc()
            if sort_direction == "ASC"
            else Notification.created_at.desc()
        )
        statement = statement.order_by(sort_order)
        async with self.database.session() as session:
            notifications = await session.scalars(statement)
            return [self._to_dto(notification) for notification in notifications]

    @staticmethod
    def _find_by_source(
        event_type: str, source_event_id: UUID | None
    ) -> Select[tuple[Notification]]:
        statement = select(Notification).where(Notification.event_type == event_type)
        if source_event_id is None:
            return statement.where(Notification.source_event_id.is_(None))
        return statement.where(Notification.source_event_id == source_event_id)

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
