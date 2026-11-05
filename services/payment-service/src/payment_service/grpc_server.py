from datetime import datetime
from decimal import Decimal
from functools import wraps
from uuid import UUID

import grpc.aio
from payment.v1 import payment_pb2, payment_pb2_grpc

from shared.auth import CurrentUser, Role, require_student_owner, require_teacher_owner
from shared.errors import DomainError, ErrorCode
from shared.events import publish_event
from shared.grpc import abort_with_domain_error, extract_principal
from shared.kafka import KafkaEventProducer

from .service import PaymentService


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

    return wrapper


def payment_to_proto(dto):
    message = payment_pb2.Payment(
        id=str(dto.id),
        booking_id=str(dto.booking_id),
        student_id=str(dto.student_id),
        teacher_id=str(dto.teacher_id),
        amount=str(dto.amount),
        currency=dto.currency,
        payment_method=dto.payment_method,
        status=dto.status,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    for field in ("paid_at", "refunded_at"):
        value = getattr(dto, field)
        if value is not None:
            setattr(message, field, value.isoformat())
    for field in ("failure_reason", "refund_reason"):
        value = getattr(dto, field)
        if value is not None:
            setattr(message, field, value)
    return message


def authorize_read(actor: CurrentUser, payment) -> None:
    if actor.role is Role.ADMIN:
        return
    if actor.role is Role.STUDENT:
        require_student_owner(actor, payment.student_id)
        return
    if actor.role is Role.TEACHER:
        require_teacher_owner(actor, payment.teacher_id)
        return
    raise DomainError(ErrorCode.FORBIDDEN, "Payment access is forbidden")


class PaymentServicer(payment_pb2_grpc.PaymentServiceServicer):
    def __init__(self, service: PaymentService, events: KafkaEventProducer) -> None:
        self.service = service
        self.events = events

    async def _publish(self, payment) -> None:
        event_type = {
            "SUCCEEDED": "payment.completed",
            "FAILED": "payment.failed",
            "REFUNDED": "payment.refunded",
        }[payment.status]
        await publish_event(
            self.events,
            event_type,
            event_type,
            payment.id,
            {
                "payment_id": str(payment.id),
                "booking_id": str(payment.booking_id),
                "student_id": str(payment.student_id),
                "teacher_id": str(payment.teacher_id),
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
        )

    @rpc_handler
    async def GetPayment(self, request, context):
        actor = extract_principal(context.invocation_metadata())
        payment = await self.service.get_payment(UUID(request.payment_id))
        if payment is not None:
            authorize_read(actor, payment)
        response = payment_pb2.GetPaymentResponse()
        if payment is not None:
            response.payment.CopyFrom(payment_to_proto(payment))
        return response

    @rpc_handler
    async def GetPaymentByBooking(self, request, context):
        actor = extract_principal(context.invocation_metadata())
        payment = await self.service.get_payment_by_booking(UUID(request.booking_id))
        if payment is not None:
            authorize_read(actor, payment)
        response = payment_pb2.GetPaymentResponse()
        if payment is not None:
            response.payment.CopyFrom(payment_to_proto(payment))
        return response

    @rpc_handler
    async def ListPayments(self, request, context):
        actor = extract_principal(context.invocation_metadata())
        if actor.role is Role.ADMIN and request.HasField("student_id"):
            student_id = UUID(request.student_id)
        else:
            if actor.student_id is None:
                raise DomainError(ErrorCode.FORBIDDEN, "Student profile is required")
            student_id = actor.student_id
        payments = await self.service.list_payments(
            student_id,
            status=request.status if request.HasField("status") else None,
            created_from=datetime.fromisoformat(request.created_from)
            if request.HasField("created_from")
            else None,
            created_to=datetime.fromisoformat(request.created_to)
            if request.HasField("created_to")
            else None,
            min_amount=Decimal(request.min_amount) if request.HasField("min_amount") else None,
            max_amount=Decimal(request.max_amount) if request.HasField("max_amount") else None,
            sort_by=request.sort_by,
            sort_direction=request.sort_direction,
        )
        return payment_pb2.ListPaymentsResponse(items=[payment_to_proto(item) for item in payments])

    @rpc_handler
    async def ProcessPayment(self, request, context):
        extract_principal(context.invocation_metadata())
        payment = await self.service.process_payment(
            UUID(request.booking_id),
            UUID(request.student_id),
            UUID(request.teacher_id),
            Decimal(request.amount),
            request.currency,
            request.payment_method,
        )
        await self._publish(payment)
        return payment_to_proto(payment)

    @rpc_handler
    async def RefundPayment(self, request, context):
        extract_principal(context.invocation_metadata())
        payment = await self.service.refund_payment(
            UUID(request.payment_id), request.reason if request.HasField("reason") else None
        )
        await self._publish(payment)
        return payment_to_proto(payment)


def create_grpc_server(service: PaymentService, port: int, events: KafkaEventProducer):
    server = grpc.aio.server()
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(service, events), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
