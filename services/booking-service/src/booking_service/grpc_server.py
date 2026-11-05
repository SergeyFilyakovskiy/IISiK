from datetime import datetime
from decimal import Decimal
from functools import wraps
from uuid import UUID

import grpc.aio
from booking.v1 import booking_pb2, booking_pb2_grpc

from shared.errors import DomainError, ErrorCode
from shared.events import publish_event
from shared.grpc import abort_with_domain_error, extract_principal, observe_rpc
from shared.kafka import KafkaEventProducer

from .workflows import BookingWorkflowService


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


def booking_to_proto(dto):
    message = booking_pb2.Booking(
        id=str(dto.id),
        lesson_id=str(dto.lesson_id),
        student_id=str(dto.student_id),
        teacher_id=str(dto.teacher_id),
        subject_id=str(dto.subject_id),
        status=dto.status,
        price=str(dto.price),
        currency=dto.currency,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    for field in ("paid_at", "completed_at", "cancelled_at"):
        value = getattr(dto, field)
        if value is not None:
            setattr(message, field, value.isoformat())
    if dto.cancel_reason is not None:
        message.cancel_reason = dto.cancel_reason
    return message


class BookingServicer(booking_pb2_grpc.BookingServiceServicer):
    def __init__(self, workflows: BookingWorkflowService, events: KafkaEventProducer) -> None:
        self.workflows = workflows
        self.events = events

    async def _publish(self, event_type: str, booking) -> None:
        await publish_event(
            self.events,
            event_type,
            event_type,
            booking.id,
            {
                "booking_id": str(booking.id),
                "lesson_id": str(booking.lesson_id),
                "student_id": str(booking.student_id),
                "teacher_id": str(booking.teacher_id),
                "status": booking.status,
            },
        )

    @rpc_handler
    async def GetBooking(self, request, context):
        booking = await self.workflows.get_booking(
            extract_principal(context.invocation_metadata()), UUID(request.booking_id)
        )
        response = booking_pb2.GetBookingResponse()
        if booking is not None:
            response.booking.CopyFrom(booking_to_proto(booking))
        return response

    @rpc_handler
    async def GetBookingByLesson(self, request, context):
        booking = await self.workflows.get_booking_by_lesson(
            extract_principal(context.invocation_metadata()), UUID(request.lesson_id)
        )
        response = booking_pb2.GetBookingResponse()
        if booking is not None:
            response.booking.CopyFrom(booking_to_proto(booking))
        return response

    @rpc_handler
    async def ListBookings(self, request, context):
        bookings = await self.workflows.list_bookings(
            extract_principal(context.invocation_metadata()),
            UUID(request.student_id) if request.HasField("student_id") else None,
            status=request.status if request.HasField("status") else None,
            created_from=datetime.fromisoformat(request.created_from)
            if request.HasField("created_from")
            else None,
            created_to=datetime.fromisoformat(request.created_to)
            if request.HasField("created_to")
            else None,
            min_price=Decimal(request.min_price) if request.HasField("min_price") else None,
            max_price=Decimal(request.max_price) if request.HasField("max_price") else None,
            sort_by=request.sort_by,
            sort_direction=request.sort_direction,
        )
        return booking_pb2.ListBookingsResponse(items=[booking_to_proto(item) for item in bookings])

    @rpc_handler
    async def BookLesson(self, request, context):
        booking = await self.workflows.book_lesson(
            extract_principal(context.invocation_metadata()), UUID(request.lesson_id)
        )
        await self._publish("booking.created", booking)
        return booking_to_proto(booking)

    @rpc_handler
    async def PayBooking(self, request, context):
        booking = await self.workflows.pay_booking(
            extract_principal(context.invocation_metadata()),
            UUID(request.booking_id),
            request.payment_method,
            UUID(request.idempotency_key),
        )
        await self._publish("booking.confirmed", booking)
        return booking_to_proto(booking)

    @rpc_handler
    async def CancelBooking(self, request, context):
        booking = await self.workflows.cancel_booking(
            extract_principal(context.invocation_metadata()),
            UUID(request.booking_id),
            request.reason if request.HasField("reason") else None,
        )
        await self._publish("booking.cancelled", booking)
        return booking_to_proto(booking)

    @rpc_handler
    async def CancelLesson(self, request, context):
        booking, _ = await self.workflows.cancel_lesson(
            extract_principal(context.invocation_metadata()),
            UUID(request.lesson_id),
            request.reason if request.HasField("reason") else None,
        )
        response = booking_pb2.BookingCancellation(cancelled=True)
        if booking is not None:
            await self._publish("booking.cancelled", booking)
            response.booking.CopyFrom(booking_to_proto(booking))
        return response

    @rpc_handler
    async def CompleteLesson(self, request, context):
        booking = await self.workflows.complete_lesson(
            extract_principal(context.invocation_metadata()), UUID(request.lesson_id)
        )
        await self._publish("booking.completed", booking)
        return booking_to_proto(booking)


def create_grpc_server(workflows: BookingWorkflowService, port: int, events: KafkaEventProducer):
    server = grpc.aio.server()
    booking_pb2_grpc.add_BookingServiceServicer_to_server(
        BookingServicer(workflows, events), server
    )
    server.add_insecure_port(f"[::]:{port}")
    return server
