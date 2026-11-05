from uuid import UUID

from shared.errors import DomainError, ErrorCode
from shared.kafka import EventEnvelope

from .identity_client import IdentityClient
from .service import NotificationService


class NotificationEventHandler:
    def __init__(self, service: NotificationService, identity: IdentityClient) -> None:
        self.service = service
        self.identity = identity

    async def __call__(self, event: EventEnvelope) -> None:
        messages = {
            "booking.created": (
                "BookingCreated",
                "Booking created",
                "Your booking is pending payment",
            ),
            "booking.cancelled": (
                "BookingCancelled",
                "Booking cancelled",
                "Your booking was cancelled",
            ),
            "payment.completed": (
                "PaymentCompleted",
                "Payment completed",
                "Your payment has succeeded",
            ),
            "booking.completed": (
                "LessonCompleted",
                "Lesson completed",
                "Your lesson is completed",
            ),
        }
        if event.event_type not in messages:
            return
        user_id = event.payload.get("user_id")
        if user_id is None:
            student_id = event.payload.get("student_id")
            if student_id is None:
                raise DomainError(ErrorCode.VALIDATION_ERROR, "Event recipient is missing")
            student = await self.identity.get_student(str(student_id))
            if student is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Student profile not found")
            user_id = student.user_id
        event_type, title, body = messages[event.event_type]
        await self.service.create_notification(
            UUID(str(user_id)), event_type, title, body, event.event_id
        )
