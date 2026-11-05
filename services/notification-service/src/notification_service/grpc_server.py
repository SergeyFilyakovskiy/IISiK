from functools import wraps
from uuid import UUID

import grpc.aio
from notification.v1 import notification_pb2, notification_pb2_grpc

from shared.auth import Role
from shared.errors import DomainError, ErrorCode
from shared.grpc import abort_with_domain_error, extract_principal, observe_rpc

from .service import NotificationService


def rpc_handler(func):
    @wraps(func)
    async def wrapper(self, request, context):
        try:
            return await func(self, request, context)
        except DomainError as error:
            await abort_with_domain_error(context, error)
        except ValueError as error:
            await abort_with_domain_error(
                context, DomainError(ErrorCode.VALIDATION_ERROR, str(error))
            )

    return observe_rpc(wrapper)


def notification_to_proto(dto):
    message = notification_pb2.Notification(
        id=str(dto.id),
        user_id=str(dto.user_id),
        event_type=dto.event_type,
        title=dto.title,
        body=dto.body,
        status=dto.status,
        created_at=dto.created_at.isoformat(),
    )
    if dto.source_event_id is not None:
        message.source_event_id = str(dto.source_event_id)
    if dto.sent_at is not None:
        message.sent_at = dto.sent_at.isoformat()
    return message


class NotificationServicer(notification_pb2_grpc.NotificationServiceServicer):
    def __init__(self, service: NotificationService) -> None:
        self.service = service

    @rpc_handler
    async def ListNotifications(self, request, context):
        actor = extract_principal(context.invocation_metadata())
        if actor.role is Role.ADMIN and request.HasField("user_id"):
            user_id = UUID(request.user_id)
        else:
            user_id = actor.user_id
        notifications = await self.service.list_notifications(
            user_id,
            request.status if request.HasField("status") else None,
            request.event_type if request.HasField("event_type") else None,
            request.sort_direction,
        )
        return notification_pb2.ListNotificationsResponse(
            items=[notification_to_proto(item) for item in notifications]
        )


def create_grpc_server(service: NotificationService, port: int):
    server = grpc.aio.server()
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(
        NotificationServicer(service), server
    )
    server.add_insecure_port(f"[::]:{port}")
    return server
